"""Test login, logout, validate-user, and profile endpoints."""

import pytest
from allauth.account.models import EmailAddress
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory


@pytest.mark.django_db
class TestLogin:
    def _create_verified_user(self, password):
        user = UserFactory(password=password)
        # UserFactory already creates an unverified EmailAddress; mark it verified
        EmailAddress.objects.filter(user=user).update(verified=True, primary=True)
        return user

    def test_login_returns_jwt_cookies(self):
        password = "Str0ng!Pass99"
        user = self._create_verified_user(password)

        client = APIClient()
        response = client.post(
            reverse("login"),
            {"email": user.email, "password": password},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.cookies.get("access_token") is not None
        assert response.cookies.get("refresh_token") is not None

    def test_login_wrong_password(self):
        user = self._create_verified_user("correct_password")

        client = APIClient()
        response = client.post(
            reverse("login"),
            {"email": user.email, "password": "wrong_password"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLogout:
    def test_logout_succeeds(self):
        password = "Str0ng!Pass99"
        user = UserFactory(password=password)
        EmailAddress.objects.filter(user=user).update(verified=True, primary=True)

        client = APIClient()
        # Login to get cookies
        login_response = client.post(
            reverse("login"),
            {"email": user.email, "password": password},
        )
        assert login_response.status_code == status.HTTP_200_OK

        response = client.post(reverse("logout"))
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestValidateUser:
    def test_validate_user_authenticated(self, authenticated_client):
        client, user = authenticated_client
        response = client.get(reverse("validate_user"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == user.email
        assert response.data["id"] == user.pk

    def test_validate_user_unauthenticated(self, unauthenticated_client):
        response = unauthenticated_client.get(reverse("validate_user"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserProfile:
    def test_profile_returns_user_data(self, authenticated_client):
        client, user = authenticated_client
        response = client.get(reverse("profile"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == user.email
        assert "application_count" in response.data
        assert "email_verified" in response.data

    def test_profile_unauthenticated(self, unauthenticated_client):
        response = unauthenticated_client.get(reverse("profile"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
