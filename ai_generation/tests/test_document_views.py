"""Test Document and DocumentVersion CRUD views."""

import pytest
from django.urls import reverse
from rest_framework import status

from accounts.tests.factories import UserFactory
from ai_generation.tests.factory import DocumentFactory, DocumentVersionFactory
from applicant_profile.tests.factory import UserContextFactory
from job_profile.tests.factories import JobDescriptionFactory


@pytest.mark.django_db
class TestDocumentViewSet:
    def test_list_documents_only_own(self, authenticated_client):
        client, user = authenticated_client
        uc = UserContextFactory(user=user)
        jd = JobDescriptionFactory(user=user)
        DocumentFactory(user=user, user_context=uc, job_description=jd)

        other = UserFactory()
        uc2 = UserContextFactory(user=other)
        jd2 = JobDescriptionFactory(user=other)
        DocumentFactory(user=other, user_context=uc2, job_description=jd2)

        url = reverse("document-list")
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

    def test_list_documents_search_by_company(self, authenticated_client):
        client, user = authenticated_client
        uc = UserContextFactory(user=user)
        jd1 = JobDescriptionFactory(user=user, company_name="Acme Corp")
        jd2 = JobDescriptionFactory(user=user, company_name="Globex Inc")
        DocumentFactory(
            user=user, user_context=uc, job_description=jd1, document_type="resume"
        )
        DocumentFactory(
            user=user, user_context=uc, job_description=jd2, document_type="resume"
        )

        url = reverse("document-list")
        response = client.get(url, {"search": "Acme"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

    def test_retrieve_document_includes_versions(self, authenticated_client):
        client, user = authenticated_client
        uc = UserContextFactory(user=user)
        jd = JobDescriptionFactory(user=user)
        doc = DocumentFactory(user=user, user_context=uc, job_description=jd)
        DocumentVersionFactory(document=doc, markdown="v1 content")
        DocumentVersionFactory(document=doc, markdown="v2 content")

        url = reverse("document-detail", args=[doc.id])
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["versions"]) == 2
        assert "company_name" in response.data
        assert "job_position" in response.data


@pytest.mark.django_db
class TestDocumentVersionHistory:
    def test_history_filtered_by_document(self, authenticated_client):
        client, user = authenticated_client
        uc = UserContextFactory(user=user)
        jd = JobDescriptionFactory(user=user)
        doc1 = DocumentFactory(
            user=user, user_context=uc, job_description=jd, document_type="resume"
        )
        doc2 = DocumentFactory(
            user=user, user_context=uc, job_description=jd, document_type="cover_letter"
        )
        DocumentVersionFactory(document=doc1, markdown="doc1 v1")
        DocumentVersionFactory(document=doc2, markdown="doc2 v1")

        url = reverse("document_version_history")
        response = client.get(url, {"document": doc1.id})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    def test_history_only_own(self, authenticated_client):
        client, user = authenticated_client
        other = UserFactory()
        uc = UserContextFactory(user=other)
        jd = JobDescriptionFactory(user=other)
        doc = DocumentFactory(user=other, user_context=uc, job_description=jd)
        DocumentVersionFactory(document=doc, markdown="not mine")

        url = reverse("document_version_history")
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0


@pytest.mark.django_db
class TestDocumentVersionViewSet:
    def test_update_version_name(self, authenticated_client):
        client, user = authenticated_client
        uc = UserContextFactory(user=user)
        jd = JobDescriptionFactory(user=user)
        doc = DocumentFactory(user=user, user_context=uc, job_description=jd)
        version = DocumentVersionFactory(document=doc, markdown="content")

        url = reverse("document-version-detail", args=[version.id])
        response = client.patch(url, {"version_name": "Renamed"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        version.refresh_from_db()
        assert version.version_name == "Renamed"
