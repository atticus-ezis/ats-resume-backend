import logging

from celery import shared_task
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist

from ai_generation.constants import COMMAND_TO_DOCUMENT_TYPES
from ai_generation.models import Document, DocumentVersion
from ai_generation.serializers import DocumentVersionResponseSerializer
from ai_generation.services import APICall, UpdateContent
from applicant_profile.models import UserContext
from job_profile.models import JobDescription
from resume_builder.utils import compute_context_hash

logger = logging.getLogger(__name__)

STALE_TASK_MESSAGE = (
    "This request is no longer valid (e.g. the page was refreshed or the app was updated). "
    "Please try again."
)


@shared_task
def generate_resume_and_cover_letter(
    user_context_id, job_description_id, command, regenerate_version, user_id
):
    try:
        user = User.objects.get(pk=user_id)
        user_context = UserContext.objects.get(pk=user_context_id, user=user)
        job_description = JobDescription.objects.get(pk=job_description_id, user=user)
    except ObjectDoesNotExist as e:
        logger.warning(
            "generate_resume_and_cover_letter: referenced object missing (stale task or post-deploy). "
            "user_id=%s user_context_id=%s job_description_id=%s error=%s",
            user_id,
            user_context_id,
            job_description_id,
            e,
        )
        raise ValueError(STALE_TASK_MESSAGE) from e
    commands = COMMAND_TO_DOCUMENT_TYPES[command]

    response_data = []
    for cmd in commands:
        # triggers? check cmd
        message = ""
        document, created = Document.objects.get_or_create(
            user=user,
            user_context=user_context,
            job_description=job_description,
            document_type=cmd,
        )

        document_version = None
        if not regenerate_version and not created:
            existing = (
                document.final_version
                or document.versions.order_by("-updated_at").first()
            )
            if existing and existing.markdown:
                document_version = existing
                message = "Found an existing document on file"
        if document_version is None:
            # does AI get called?
            try:
                chat_responses = APICall(
                    user_context=user_context,
                    job_description=job_description,
                    command=cmd,
                ).execute()
            except Exception:
                logger.exception("AI generation failed for document type %s", cmd)
                raise
            context_hash = compute_context_hash(chat_responses)
            (
                document_version,
                version_created,
            ) = DocumentVersion.objects.get_or_create(
                document=document,
                context_hash=context_hash,
                defaults={"markdown": chat_responses},
            )
            if not version_created:
                message = "The contents of the regenerated document match the original. Consider adding additional instructions."

        serializer = DocumentVersionResponseSerializer(document_version)
        item = {"document_version": serializer.data}
        if message:
            item["message"] = message
        response_data.append(item)

    return response_data


@shared_task
def update_content(document_version_id, instructions):
    try:
        document_version = DocumentVersion.objects.get(pk=document_version_id)
    except DocumentVersion.DoesNotExist as e:
        logger.warning(
            "update_content: DocumentVersion missing (stale task or post-deploy). "
            "document_version_id=%s error=%s",
            document_version_id,
            e,
        )
        raise ValueError(STALE_TASK_MESSAGE) from e
    try:
        markdown_response = UpdateContent(instructions, document_version).execute()
    except Exception:
        logger.exception("Failed to update content for version %s", document_version_id)
        raise
    new_version = DocumentVersion.objects.create(
        document=document_version.document,
        markdown=markdown_response,
    )
    serializer = DocumentVersionResponseSerializer(new_version)
    return serializer.data
