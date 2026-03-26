import os

from celery import Celery
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_project.settings")

app = Celery(
    "import_export_extensions",
    backend=settings.CELERY_BACKEND,
    broker=settings.CELERY_BROKER,
)

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()
