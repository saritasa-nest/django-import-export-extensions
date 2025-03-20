import pathlib

import decouple

# Build paths inside the project like this: BASE_DIR / "subdir"
BASE_DIR = pathlib.Path(__file__).resolve().parent

SECRET_KEY = "a87082n4v52u4rnvk2edv128eudfvn5"  # noqa: S105

ALLOWED_HOSTS = ["*"]

DEBUG = True
TESTING = False

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "django_probes",
    "django_extensions",
    "import_export",
    "import_export_extensions",
    "test_project.fake_app",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "test_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "test_project.wsgi.application"

# Database
# https://docs.djangoproject.com/en/dev/ref/settings/#std-setting-DATABASES

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "ATOMIC_REQUESTS": True,
        "CONN_MAX_AGE": 600,
        "USER": decouple.config(
            "DB_USER",
            default="django-import-export-extensions-user",
        ),
        "NAME": decouple.config(
            "DB_NAME",
            default="django-import-export-extensions-dev",
        ),
        "PASSWORD": decouple.config("DB_PASSWORD", default="testpass"),
        "HOST": decouple.config("DB_HOST", default="postgres"),
        "PORT": decouple.config("DB_PORT", default=5432, cast=int),
    },
}

AUTH_USER_MODEL = "auth.User"

# Internationalization
# https://docs.djangoproject.com/en/dev/topics/i18n/

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/

STATIC_URL = "/static/"
MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"
STATIC_ROOT = BASE_DIR / "static"

# https://docs.djangoproject.com/en/dev/ref/settings/#storages
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
    "django_import_export_extensions": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}

STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
)

# Configure `drf-spectacular` to check it works for import-export API
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "COMPONENT_SPLIT_REQUEST": True,  # Allows to upload import file from Swagger UI
}

# Celery settings

redis_host = decouple.config("REDIS_HOST", default="redis")
redis_port = decouple.config("REDIS_PORT", default=6379, cast=int)
redis_db = decouple.config("REDIS_DB", default=1, cast=int)

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_STORE_EAGER_RESULT = True

CELERY_TASK_SERIALIZER = "pickle"
CELERY_ACCEPT_CONTENT = ["pickle", "json"]

CELERY_TASK_ROUTES = {}
CELERY_BROKER = f"redis://{redis_host}:{redis_port}/{redis_db}"
CELERY_BACKEND = f"redis://{redis_host}:{redis_port}/{redis_db}"
CELERY_TASK_DEFAULT_QUEUE = "development"

# https://docs.djangoproject.com/en/dev/ref/settings/#std-setting-DEFAULT_AUTO_FIELD
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

if DEBUG:
    INSTALLED_APPS += ("debug_toolbar",)
    MIDDLEWARE += ("debug_toolbar.middleware.DebugToolbarMiddleware",)

    def _show_toolbar_callback(request) -> bool:
        """Show debug toolbar exclude testing."""
        from django.conf import settings

        return not settings.TESTING

    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": _show_toolbar_callback,
    }
