"""
Django settings for resume_builder project.
"""

import os
import sys
from datetime import timedelta
from pathlib import Path

import dj_database_url
import environ
from django.core.management.utils import get_random_secret_key

# Set library path for WeasyPrint on macOS
if sys.platform == "darwin":
    homebrew_paths = ["/opt/homebrew/lib", "/usr/local/lib"]
    for lib_path in homebrew_paths:
        if os.path.exists(lib_path):
            current_path = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
            if lib_path not in current_path:
                os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = (
                    f"{lib_path}:{current_path}" if current_path else lib_path
                )
            break


BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()

local_env = BASE_DIR / ".env"
if local_env.exists():
    environ.Env.read_env(local_env)

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

SECRET_KEY = env.str("SECRET_KEY", default=get_random_secret_key())
DEBUG = env.bool("DEBUG", default=False)
OPENAI_API_KEY = env.str("OPENAI_API_KEY", "fake-key-123")

# ---------------------------------------------------------------------------
# Domains + Origins
# ---------------------------------------------------------------------------

# Domains (www.example.com)
BACKEND_DOMAIN = env.str("BACKEND_DOMAIN", "localhost")  # api.ats-resume-builder.com
FRONTEND_DOMAIN = env.str("FRONTEND_DOMAIN", "localhost")  # www.ats-resume-builder.com
# Parent domain for cookies shared across api + www (e.g. .ats-resume-builder.com)
# Leave unset for localhost
SHARED_DOMAIN = env.str("SHARED_DOMAIN", default="")

# origins (https://www.example.com)
BACKEND_ORIGIN = env.str(
    "BACKEND_ORIGIN", "http://localhost:8000"
)  # https://api.ats-resume-builder.com
FRONTEND_ORIGIN = env.str(
    "FRONTEND_ORIGIN", "http://localhost:3000"
)  # https://www.ats-resume-builder.com


# ---------------------------------------------------------------------------
# Hosts / CORS / CSRF
# ---------------------------------------------------------------------------

ALLOWED_HOSTS = [BACKEND_DOMAIN, "localhost", "127.0.0.1"]
### CORS
CORS_ALLOWED_ORIGINS = [
    FRONTEND_ORIGIN,
    BACKEND_ORIGIN,
]  # backend needs https://api.ats-resume-builder.com for admin/Swagger
CORS_ALLOW_CREDENTIALS = True
### CSRF - must include BACKEND_ORIGIN for same-origin requests (Swagger, admin)
CSRF_TRUSTED_ORIGINS = [FRONTEND_ORIGIN, BACKEND_ORIGIN]
CSRF_COOKIE_DOMAIN = SHARED_DOMAIN or None
SESSION_COOKIE_DOMAIN = SHARED_DOMAIN or None


# ---------------------------------------------------------------------------
# Installed apps
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    #
    "corsheaders",
    "django.contrib.sites",
    # account
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    # rest framework
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "rest_framework.authtoken",
    "dj_rest_auth",
    "dj_rest_auth.registration",
    # apps
    "accounts",
    "applicant_profile",
    "job_profile",
    "ai_generation",
    # third party
    "drf_spectacular",
    "django_celery_results",
]

# ---------------------------------------------------------------------------
# Sites
# ---------------------------------------------------------------------------

SITE_DOMAIN = env.str("BACKEND_DOMAIN", "localhost")
SITE_NAME = "Resume Builder"
SITE_ID = 1

# ---------------------------------------------------------------------------
# REST Framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "dj_rest_auth.jwt_auth.JWTCookieAuthentication",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

REST_AUTH = {
    "USE_JWT": True,
    "JWT_AUTH_COOKIE_USE_CSRF": True,
    "JWT_AUTH_HTTPONLY": True,
    "JWT_AUTH_SAMESITE": env.str("JWT_AUTH_SAMESITE", "Lax"),
    "JWT_AUTH_SECURE": not DEBUG,
    "JWT_AUTH_COOKIE": "access_token",
    "JWT_AUTH_REFRESH_COOKIE": "refresh_token",
    "REGISTER_SERIALIZER": "accounts.serializers.CustomRegisterSerializer",
    "SESSION_LOGIN": False,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Resume Builder API",
    "DESCRIPTION": "API documentation for Resume Builder application",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "AUTHENTICATION_WHITELIST": [
        "dj_rest_auth.jwt_auth.JWTCookieAuthentication",
    ],
}

# ---------------------------------------------------------------------------
# Allauth
# ---------------------------------------------------------------------------

ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_ADAPTER = "accounts.adapters.CustomAccountAdapter"
ACCOUNT_DEFAULT_HTTP_PROTOCOL = env.str("HTTP_PROTOCOL", "http")
ACCOUNT_EMAIL_SUBJECT_PREFIX = SITE_NAME
ACCOUNT_PASSWORD_RESET_EXPIRE_DAYS = 1

SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
# Google has already verified the email; allauth marks it verified=True in the
# DB without sending a redundant verification email.
SOCIALACCOUNT_EMAIL_VERIFICATION = "none"

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": env.str("GOOGLE_CLIENT_ID", "fake-id-123"),
            "secret": env.str("GOOGLE_CLIENT_SECRET", "fake-secret-123"),
            "key": "",
        },
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    }
}

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

EMAIL_TIMEOUT = 10

if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = "smtp.gmail.com"
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = "ats.resume.builder.business@gmail.com"
    EMAIL_HOST_PASSWORD = env.str("EMAIL_APP_PASSWORD", "")
    DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
    SERVER_EMAIL = EMAIL_HOST_USER

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "resume_builder.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

WSGI_APPLICATION = "resume_builder.wsgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

db_url = env.str("DATABASE_URL", default=None)
if db_url:
    DATABASES = {"default": dj_database_url.parse(db_url, conn_max_age=600)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------

CELERY_BROKER_URL = env.str("REDIS_HOST", default="redis://localhost:6379/0")
CELERY_TASK_TIME_LIMIT = 5 * 60
CELERY_RESULT_BACKEND = "django-db"

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": True,
        },
        "accounts": {
            "handlers": ["console"],
            "level": "INFO" if DEBUG else "WARNING",
            "propagate": False,
        },
        "ai_generation": {
            "handlers": ["console"],
            "level": "INFO" if DEBUG else "WARNING",
            "propagate": False,
        },
        "applicant_profile": {
            "handlers": ["console"],
            "level": "INFO" if DEBUG else "WARNING",
            "propagate": False,
        },
        "job_profile": {
            "handlers": ["console"],
            "level": "INFO" if DEBUG else "WARNING",
            "propagate": False,
        },
    },
}
