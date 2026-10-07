import pytest
import pytest_mock
from django.contrib.auth.models import User
from django.test.client import Client
from django.urls import reverse
from rest_framework import status

from example.app import factories
from import_export_extensions import models as ie_models


def test_celery_export_status_view_during_export(
    client: Client,
    superuser: User,
    mocker: pytest_mock.MockerFixture,
):
    """Test export status page when export in progress."""
    client.force_login(superuser)

    mocker.patch("import_export_extensions.tasks.export_data_task.apply_async")
    artist_export_job = factories.ArtistExportJobFactory.create()
    artist_export_job.export_status = (
        ie_models.ExportJob.ExportStatus.EXPORTING
    )
    artist_export_job.save()

    response = client.get(
        path=reverse(
            "admin:app_artist_export_job_status",
            kwargs={"job_id": artist_export_job.pk},
        ),
    )

    expected_export_job_url = reverse(
        "admin:export_job_progress",
        kwargs={"job_id": artist_export_job.id},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.context["export_job_url"] == expected_export_job_url


@pytest.mark.parametrize(
    argnames="incorrect_job_status",
    argvalues=[
        ie_models.ExportJob.ExportStatus.CREATED,
        ie_models.ExportJob.ExportStatus.EXPORTING,
        ie_models.ExportJob.ExportStatus.CANCELLED,
    ],
)
def test_celery_export_results_view_redirect_to_status_page(
    client: Client,
    superuser: User,
    incorrect_job_status: ie_models.ExportJob.ExportStatus,
    mocker: pytest_mock.MockerFixture,
):
    """Test redirect to export status page when job in not results statuses."""
    client.force_login(superuser)

    mocker.patch("import_export_extensions.tasks.export_data_task.apply_async")
    artist_export_job = factories.ArtistExportJobFactory.create()
    artist_export_job.export_status = incorrect_job_status
    artist_export_job.save()

    response = client.get(
        path=reverse(
            "admin:app_artist_export_job_results",
            kwargs={"job_id": artist_export_job.pk},
        ),
    )

    expected_redirect_url = reverse(
        "admin:app_artist_export_job_status",
        kwargs={"job_id": artist_export_job.pk},
    )
    assert response.status_code == status.HTTP_302_FOUND
    assert response.url == expected_redirect_url
