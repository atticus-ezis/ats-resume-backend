import pytest
from allauth.account.models import EmailAddress
from rest_framework.test import APIClient

from accounts.tests.conftest import (
    generate_email_verification_token,
)


@pytest.mark.django_db
class TestUserRegistration:
    @pytest.fixture
    def client(self):
        return APIClient()

    def test_confirm_email_verification(
        self,
        confirm_email_verification_url,
        login_url,
        registration_url,
    ):
        from faker import Faker

        fake = Faker()
        email = fake.email()
        password = fake.password()

        # Register user (don't use UserFactory - let registration create the user)
        register_response = APIClient().post(
            registration_url,
            {
                "email": email,
                "password1": password,
                "password2": password,
            },
        )
        assert (
            register_response.status_code == 201
        ), f"expected 201 but got {register_response.status_code} with response: {register_response.data}"
        assert (
            register_response.data["detail"] == "Verification e-mail sent."
        ), f"expected 'Verification e-mail sent.' but got {register_response.data.get('detail', 'no detail')}"

        # Get the newly created user and email address
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.get(email=email)
        email_address = EmailAddress.objects.get(user=user, email=email)
        assert email_address.verified is False, "email should not be verified yet"

        # shouldn't be able to login until confirmed
        bad_response = APIClient().post(
            login_url,
            {
                "email": email,
                "password": password,
            },
        )
        assert (
            bad_response.status_code == 400
        ), f"expected 400 but got {bad_response.status_code} with response: {bad_response.data}"

        # Generate verification token from the newly created email address
        email_verification_token = generate_email_verification_token(email)

        # Confirm email
        confirm_response = APIClient().post(
            confirm_email_verification_url,
            {
                "key": email_verification_token,
            },
        )
        assert (
            confirm_response.status_code == 200
        ), f"email not confirmed: expected 200 but got {confirm_response.status_code} with response: {confirm_response.data}"

        # Refresh email address from database to get updated status
        email_address.refresh_from_db()
        assert email_address.verified is True, "email not confirmed"

        # Login user
        response = APIClient().post(
            login_url,
            {
                "email": email,
                "password": password,
            },
        )

        assert (
            response.status_code == 200
        ), f"expected 200 but got {response.status_code} with response: {response.data}"
