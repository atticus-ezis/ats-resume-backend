"""Test PDF download action and cross-user permission fix."""

from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status

from accounts.tests.factories import UserFactory
from ai_generation.tests.factory import DocumentFactory, DocumentVersionFactory
from applicant_profile.tests.factory import UserContextFactory
from job_profile.tests.factories import JobDescriptionFactory


@pytest.mark.django_db
class TestPDFDownload:
    def _create_version(self, user):
        uc = UserContextFactory(user=user)
        jd = JobDescriptionFactory(user=user)
        doc = DocumentFactory(user=user, user_context=uc, job_description=jd)
        return DocumentVersionFactory(document=doc, markdown="# Test Resume")

    @patch("ai_generation.services.HTML")
    def test_pdf_download_returns_pdf(self, mock_html_cls, authenticated_client):
        client, user = authenticated_client
        version = self._create_version(user)

        mock_html_cls.return_value.write_pdf.return_value = b"%PDF-fake-bytes"

        url = reverse("document-version-detail", args=[version.id]) + "pdf/"
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"
        assert response["Content-Disposition"].startswith("attachment;")

    def test_pdf_download_other_users_version_denied(self, authenticated_client):
        """Regression: user B must NOT be able to download user A's PDF."""
        client, _ = authenticated_client
        other_user = UserFactory()
        other_version = self._create_version(other_user)

        url = reverse("document-version-detail", args=[other_version.id]) + "pdf/"
        response = client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
