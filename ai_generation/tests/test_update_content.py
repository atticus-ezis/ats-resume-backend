"""Test UpdateContentView and the update_content Celery task."""

from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status

from accounts.tests.factories import UserFactory
from ai_generation.models import DocumentVersion
from ai_generation.tasks import update_content
from ai_generation.tests.factory import DocumentFactory, DocumentVersionFactory
from applicant_profile.tests.factory import UserContextFactory
from job_profile.tests.factories import JobDescriptionFactory


@pytest.mark.django_db
class TestUpdateContentView:
    def _setup(self, user):
        uc = UserContextFactory(user=user)
        jd = JobDescriptionFactory(user=user)
        doc = DocumentFactory(user=user, user_context=uc, job_description=jd)
        version = DocumentVersionFactory(document=doc, markdown="original markdown")
        return version

    def test_update_content_returns_task_id(self, authenticated_client):
        client, user = authenticated_client
        version = self._setup(user)
        url = reverse("update_content")

        response = client.post(
            url,
            {"document_version_id": version.id, "instructions": "Make it better"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "task_id" in response.data

    def test_update_content_requires_instructions(self, authenticated_client):
        client, user = authenticated_client
        version = self._setup(user)
        url = reverse("update_content")

        response = client.post(
            url,
            {"document_version_id": version.id},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_content_unauthenticated(self, unauthenticated_client):
        url = reverse("update_content")
        response = unauthenticated_client.post(
            url, {"document_version_id": 1, "instructions": "test"}, format="json"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_content_other_users_version(self, authenticated_client):
        client, user = authenticated_client
        other_user = UserFactory()
        other_version = self._setup(other_user)
        url = reverse("update_content")

        response = client.post(
            url,
            {"document_version_id": other_version.id, "instructions": "hack"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestUpdateContentTask:
    @patch("ai_generation.services.api_call", return_value="# Updated markdown")
    def test_task_creates_new_version(self, mock_api):
        doc = DocumentFactory()
        version = DocumentVersionFactory(document=doc, markdown="original markdown")

        result = update_content(
            document_version_id=version.id,
            instructions="Make it better",
        )

        assert DocumentVersion.objects.filter(document=doc).count() == 2
        assert result["markdown"] == "# Updated markdown"
        mock_api.assert_called_once()

    @patch("ai_generation.services.api_call", return_value=None)
    def test_task_ai_failure_raises(self, mock_api):
        doc = DocumentFactory()
        version = DocumentVersionFactory(document=doc, markdown="content")

        with pytest.raises(Exception, match="Failed to update content"):
            update_content(
                document_version_id=version.id,
                instructions="test",
            )
