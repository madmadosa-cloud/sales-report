"""
사회복지시설 매출분석 웹 프로그램 설정

Author: madmadosa-cloud
License: MIT
"""

import os
import secrets
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from sales_report.paths import BUNDLE_DIR, DATA_DIR, is_frozen

IS_FROZEN = is_frozen()
BASE_DIR = BUNDLE_DIR

_env_file = DATA_DIR / ".env"
if _env_file.exists():
    try:
        from dotenv import load_dotenv

        load_dotenv(_env_file)
    except ImportError:
        pass

_secret = os.environ.get("DJANGO_SECRET_KEY") or os.environ.get("SECRET_KEY")
if not _secret and "test" in sys.argv:
    _secret = "django-insecure-test-only-do-not-use-in-production"
if not _secret and IS_FROZEN:
    _secret_file = DATA_DIR / ".django_secret"
    if _secret_file.is_file():
        _secret = _secret_file.read_text(encoding="utf-8").strip()
    else:
        _secret = secrets.token_urlsafe(50)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _secret_file.write_text(_secret, encoding="utf-8")
if not _secret:
    raise ImproperlyConfigured(
        "SECRET_KEY is not set. Copy .env.example to .env and set DJANGO_SECRET_KEY."
    )
SECRET_KEY = _secret

if IS_FROZEN:
    DEBUG = False
else:
    DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_htmx",
    "sales_analysis.apps.SalesAnalysisConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
]
if IS_FROZEN:
    MIDDLEWARE.append("whitenoise.middleware.WhiteNoiseMiddleware")
MIDDLEWARE.extend(
    [
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
        "django_htmx.middleware.HtmxMiddleware",
    ]
)

ROOT_URLCONF = "sales_report.urls"

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
                "sales_analysis.context_processors.app_meta",
            ],
        },
    },
]

WSGI_APPLICATION = "sales_report.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
if IS_FROZEN:
    STATICFILES_DIRS: list[Path] = []
else:
    STATICFILES_DIRS = [BASE_DIR / "static"]

if IS_FROZEN:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
    WHITENOISE_ROOT = STATIC_ROOT

MEDIA_URL = "media/"
MEDIA_ROOT = DATA_DIR / "media"

LOG_DIR = DATA_DIR / "logs"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REPORT_FONT_PATH = os.environ.get("REPORT_FONT_PATH", "")

DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
