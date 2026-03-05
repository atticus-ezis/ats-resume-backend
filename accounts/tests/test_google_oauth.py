"""Light test for GoogleLoginView — only tests input validation, not the full token exchange."""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestGoogleOAuth:
    def test_google_login_missing_code(self):
        client = APIClient()
        response = client.post(reverse("google_login"), {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
