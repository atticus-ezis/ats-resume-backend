import logging

from dj_rest_auth.registration.views import (
    VerifyEmailView as DjRestVerifyEmailView,
)
from dj_rest_auth.views import LoginView, LogoutView
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated

from accounts.serializers import UserProfileSerializer

logger = logging.getLogger(__name__)

# example google client id: 1234567890-abc123def456.apps.googleusercontent.com


class UserProfileView(RetrieveAPIView):
    """
    GET /api/accounts/profile/ — returns the authenticated user's profile
    as specified by UserProfileSerializer. No pk in URL; uses request.user.
    """

    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class CSRFExemptLoginView(LoginView):
    """
    Login view with CSRF exemption for REST API usage.
    This allows login without CSRF tokens while keeping CSRF protection for other endpoints.
    """

    permission_classes = [AllowAny]  # Explicitly allow unauthenticated access
    authentication_classes = []  # Disable authentication for login endpoint

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class CustomLogoutView(LogoutView):
    """
    Custom logout view that extracts the refresh token from HttpOnly cookies.
    Since the frontend can't access HttpOnly cookies, we extract it on the backend
    and add it to request.data for proper token blacklisting.
    """

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        # Get the refresh token cookie name from settings
        refresh_cookie_name = getattr(settings, "REST_AUTH", {}).get(
            "JWT_AUTH_REFRESH_COOKIE", "refresh_token"
        )

        # Extract refresh token from HttpOnly cookie
        refresh_token = request.COOKIES.get(refresh_cookie_name)

        if refresh_token:
            # Access request.data to trigger parsing, then inject the refresh
            # token into the mutable backing store for token blacklisting.
            data = request.data
            if isinstance(data, dict):
                data["refresh"] = refresh_token
            else:
                request._full_data = {"refresh": refresh_token}

        return super().post(request, *args, **kwargs)


class CustomVerifyEmailView(DjRestVerifyEmailView):
    permission_classes = [AllowAny]
    authentication_classes = []
