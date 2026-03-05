"""
URL configuration for resume_builder project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from dj_rest_auth.jwt_auth import get_refresh_view
from dj_rest_auth.registration.views import (
    RegisterView,
    ResendEmailVerificationView,
)
from dj_rest_auth.views import (
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetView,
    UserDetailsView,
)
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from django.views.generic import TemplateView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenVerifyView

from accounts.social_views import GoogleLoginView
from accounts.views import (
    CSRFExemptLoginView,
    CustomLogoutView,
    CustomVerifyEmailView,
    UserProfileView,
)
from ai_generation.views import (
    DocumentVersionHistory,
    DocumentVersionViewSet,
    DocumentViewSet,
    GenerateResumeAndCoverLetterView,
    UpdateContentView,
)
from applicant_profile.views import UserContextViewSet
from job_profile.views import JobDescriptionViewSet
from resume_builder.views import TaskResultView

router = DefaultRouter()
router.register(r"applicant", UserContextViewSet, basename="applicant")
router.register(r"job", JobDescriptionViewSet, basename="job")
router.register(r"document", DocumentViewSet, basename="document")
router.register(
    r"document-version", DocumentVersionViewSet, basename="document-version"
)


@api_view(["GET"])
def validate_user(request):
    user = request.user
    if user.is_authenticated:
        return Response(
            status=status.HTTP_200_OK, data={"email": user.email, "id": user.pk}
        )
    return Response(
        status=status.HTTP_401_UNAUTHORIZED,
        data={"detail": "user is not authenticated"},
    )


def health_check(request):
    return HttpResponse("ok", status=200)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health-check/", health_check, name="health_check"),
    # path("applicant/", include("applicant_profile.urls")),
    path(
        "accounts/", include("allauth.account.urls")
    ),  # Required for account_confirm_email URL name
    path("accounts/social/", include("allauth.socialaccount.urls")),
    path(
        "api/",
        include(
            [
                path(
                    "accounts/",
                    include(
                        [
                            path("profile/", UserProfileView.as_view(), name="profile"),
                            path("validate-user/", validate_user, name="validate_user"),
                            # registration / confirm email
                            path(
                                "registration/",
                                RegisterView.as_view(),
                                name="register",
                            ),
                            path(
                                "registration/resend-email/",
                                ResendEmailVerificationView.as_view(),
                                name="resend_email",
                            ),
                            path(
                                "registration/verify-email/",
                                CustomVerifyEmailView.as_view(),
                                name="custom_verify_email",
                            ),
                            path(
                                "login/",
                                CSRFExemptLoginView.as_view(),
                                name="login",
                            ),
                            path("logout/", CustomLogoutView.as_view(), name="logout"),
                            path(
                                "user/", UserDetailsView.as_view(), name="user_details"
                            ),
                            path(
                                "token/refresh/",
                                get_refresh_view().as_view(),
                                name="token_refresh",
                            ),
                            path(
                                "token/verify/",
                                TokenVerifyView.as_view(),
                                name="token_verify",
                            ),
                            # reset password
                            path(
                                "password/reset/",
                                PasswordResetView.as_view(),
                                name="rest_password_reset",
                            ),
                            path(
                                "password/reset/confirm/<uidb64>/<token>/",
                                TemplateView.as_view(
                                    template_name="accounts/password_reset_confirm.html"
                                ),
                                name="password_reset_confirm",  # placeholder
                            ),
                            path(
                                "password/reset/confirm/",
                                PasswordResetConfirmView.as_view(),
                                name="custom_password_reset_confirm",
                            ),
                            path(
                                "password/change/",
                                PasswordChangeView.as_view(),
                                name="password_change",
                            ),
                            path(
                                "auth/google/",
                                GoogleLoginView.as_view(),
                                name="google_login",
                            ),
                        ]
                    ),
                ),
                path(
                    "generate-resume-and-cover-letter/",
                    GenerateResumeAndCoverLetterView.as_view(),
                    name="generate_resume_and_cover_letter",
                ),
                path(
                    "update-content/",
                    UpdateContentView.as_view(),
                    name="update_content",
                ),
                path(
                    "document-version-history/",
                    DocumentVersionHistory.as_view(),
                    name="document_version_history",
                ),
                path("", include(router.urls)),
                path(
                    "task-result/<str:task_id>/",
                    TaskResultView.as_view(),
                    name="task_result",
                ),
            ]
        ),
    ),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
