from django.tasks import task

from celery import shared_task

from . import models


@shared_task()
def parse_data_task(job_id: int) -> None:
    """Async task for starting data parsing."""
    models.ImportJob.objects.get(pk=job_id).parse_data()


@shared_task()
def import_data_task(job_id: int) -> None:
    """Async task for starting data import."""
    models.ImportJob.objects.get(pk=job_id).import_data()


@shared_task()
def export_data_task(job_id: int) -> None:
    """Async task for starting data export."""
    job = models.ExportJob.objects.get(id=job_id)
    job.export_data()


# TODO(otto): merge this task in one function and use decorator dynamically if possible
@task()
def export_data_django_task(job_id: int):
    """Async task for starting data export."""
    job = models.ExportJob.objects.get(id=job_id)
    job.export_data()
