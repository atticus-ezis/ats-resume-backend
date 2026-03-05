"""Test the Celery generation task with mocked OpenAI."""

from unittest.mock import patch

import pytest

from ai_generation.models import Document, DocumentVersion
from ai_generation.tasks import generate_resume_and_cover_letter
from ai_generation.tests.factory import DocumentFactory, DocumentVersionFactory
from applicant_profile.tests.factory import UserContextFactory
from job_profile.tests.factories import JobDescriptionFactory


@pytest.mark.django_db
class TestGenerationTask:
    @patch("ai_generation.services.api_call", return_value="# Mocked Resume")
    def test_generate_resume_creates_document_and_version(
        self, mock_api, authenticated_client
    ):
        _, user = authenticated_client
        uc = UserContextFactory(user=user)
        jd = JobDescriptionFactory(user=user)

        result = generate_resume_and_cover_letter(
            user_context_id=uc.id,
            job_description_id=jd.id,
            command="generate_resume",
            regenerate_version=False,
            user_id=user.id,
        )

        assert Document.objects.filter(user=user).count() == 1
        assert DocumentVersion.objects.count() == 1
        assert result[0]["document_version"]["markdown"] == "# Mocked Resume"
        mock_api.assert_called_once()

    def test_generate_reuses_existing_version(self, authenticated_client):
        _, user = authenticated_client
        uc = UserContextFactory(user=user)
        jd = JobDescriptionFactory(user=user)
        doc = DocumentFactory(
            user=user, user_context=uc, job_description=jd, document_type="resume"
        )
        existing = DocumentVersionFactory(document=doc, markdown="existing content")

        result = generate_resume_and_cover_letter(
            user_context_id=uc.id,
            job_description_id=jd.id,
            command="generate_resume",
            regenerate_version=False,
            user_id=user.id,
        )

        assert DocumentVersion.objects.count() == 1
        assert result[0]["document_version"]["id"] == existing.id
        assert "existing" in result[0].get("message", "").lower()

    @patch("ai_generation.services.api_call", return_value="# Regenerated")
    def test_generate_with_regenerate_calls_ai(self, mock_api, authenticated_client):
        _, user = authenticated_client
        uc = UserContextFactory(user=user)
        jd = JobDescriptionFactory(user=user)
        doc = DocumentFactory(
            user=user, user_context=uc, job_description=jd, document_type="resume"
        )
        DocumentVersionFactory(document=doc, markdown="old content")

        result = generate_resume_and_cover_letter(
            user_context_id=uc.id,
            job_description_id=jd.id,
            command="generate_resume",
            regenerate_version=True,
            user_id=user.id,
        )

        assert DocumentVersion.objects.count() == 2
        assert result[0]["document_version"]["markdown"] == "# Regenerated"
        mock_api.assert_called_once()

    @patch("ai_generation.services.api_call", return_value="# Mocked Content")
    def test_generate_both_creates_two_documents(self, mock_api, authenticated_client):
        _, user = authenticated_client
        uc = UserContextFactory(user=user)
        jd = JobDescriptionFactory(user=user)

        result = generate_resume_and_cover_letter(
            user_context_id=uc.id,
            job_description_id=jd.id,
            command="generate_both",
            regenerate_version=False,
            user_id=user.id,
        )

        assert Document.objects.filter(user=user).count() == 2
        assert len(result) == 2
        doc_types = {r["document_version"]["document"]["type"] for r in result}
        assert doc_types == {"resume", "cover_letter"}

    @patch("ai_generation.services.api_call", return_value=None)
    def test_generate_ai_failure_raises(self, mock_api, authenticated_client):
        _, user = authenticated_client
        uc = UserContextFactory(user=user)
        jd = JobDescriptionFactory(user=user)

        with pytest.raises(Exception, match="Failed to generate"):
            generate_resume_and_cover_letter(
                user_context_id=uc.id,
                job_description_id=jd.id,
                command="generate_resume",
                regenerate_version=False,
                user_id=user.id,
            )
