from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models

from applicant_profile.models import UserContext
from job_profile.models import JobDescription
from resume_builder.utils import compute_context_hash

CONSTRAINT_UNIQUE_TYPE = "unique_document_type_per_user_context_and_job_description"
CONSTRAINT_UNIQUE_VERSION_NAME = "unique_name_per_document"
CONSTRAINT_UNIQUE_VERSION_MARKDOWN = "unique_markdown_per_document"


class Document(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
    user_context = models.ForeignKey(
        UserContext, on_delete=models.CASCADE, related_name="documents"
    )
    job_description = models.ForeignKey(
        JobDescription, on_delete=models.CASCADE, related_name="documents"
    )
    document_type = models.CharField(
        max_length=255, choices=[("resume", "Resume"), ("cover_letter", "Cover Letter")]
    )
    final_version = models.ForeignKey(
        "DocumentVersion",
        on_delete=models.SET_NULL,
        related_name="final_version",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.final_version_id and self.final_version.document_id != self.pk:
            raise ValidationError("final_version must belong to this document")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.job_description.company_name} - {self.document_type}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "user_context", "job_description", "document_type"],
                name=CONSTRAINT_UNIQUE_TYPE,
            )
        ]


class DocumentVersion(models.Model):
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="versions"
    )
    markdown = models.TextField(null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version_name = models.CharField(max_length=255, null=True, blank=True)
    context_hash = models.CharField(max_length=64, db_index=True, blank=True, null=True)

    def __str__(self):
        return f"Version {self.id} of {self.document.job_description.company_name} - {self.document.document_type} - {self.created_at}"

    def save(self, *args, **kwargs):
        if not self.pk and not self.version_name:
            existing_versions = self.document.versions.count()
            if existing_versions > 0:
                self.version_name = f"{str(self.document)} - {existing_versions + 1}"
            else:
                self.version_name = f"{str(self.document)} - 1"
        if self.markdown is not None:
            self.context_hash = compute_context_hash(self.markdown)
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["document", "version_name"],
                name=CONSTRAINT_UNIQUE_VERSION_NAME,
            ),
            models.UniqueConstraint(
                fields=["document", "context_hash"],
                name=CONSTRAINT_UNIQUE_VERSION_MARKDOWN,
            ),
        ]
