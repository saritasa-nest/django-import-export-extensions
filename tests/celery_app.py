import os

from django.conf import settings

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

app = Celery(
    "import_export_extensions",
    backend=settings.CELERY_BACKEND,
    broker=settings.CELERY_BROKER,
)

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()
