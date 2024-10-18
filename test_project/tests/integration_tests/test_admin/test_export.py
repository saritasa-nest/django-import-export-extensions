"""There are kind a functional tests for export using Django Admin."""

from django.contrib.auth.models import User
from django.test.client import Client
from django.urls import reverse

from rest_framework import status

import pytest
import pytest_mock
from celery import states

from import_export_extensions.models import ExportJob
from test_project.fake_app.factories import ArtistExportJobFactory


@pytest.mark.usefixtures("existing_artist")
@pytest.mark.django_db(transaction=True)
def test_export_using_admin_model(client: Client, superuser: User):
    """Test entire exporting process using Django Admin.

    There is following workflow:
        1. Go to Artist Export page
        2. Start Export Job with chosen file format (csv)
        3. Redirect to export job result page through the status page

    """
    client.force_login(superuser)

    # Make get request to admin export page
    export_get_response = client.get(
        path=reverse("admin:fake_app_artist_export"),
    )
    assert export_get_response.status_code == status.HTTP_200_OK

    # Start export job using admin panel
    start_export_response = client.post(
        path=reverse("admin:fake_app_artist_export"),
        data={
            "format": 0,
        },
    )
    assert start_export_response.status_code == status.HTTP_302_FOUND

    # Go to redirected page after export is finished
    status_response = client.get(start_export_response.url)
    assert status_response.status_code == status.HTTP_302_FOUND

    result_response = client.get(status_response.url)
    assert result_response.status_code == status.HTTP_200_OK

    assert ExportJob.objects.exists()
    export_job = ExportJob.objects.first()
    assert export_job.export_status == ExportJob.ExportStatus.EXPORTED


@pytest.mark.django_db(transaction=True)
def test_export_progress_for_sync_mode(
    client: Client,
    superuser: User,
):
    """Test export job admin progress page."""
    client.force_login(superuser)

    artist_export_job = ArtistExportJobFactory()
    artist_export_job.refresh_from_db()

    response = client.post(
        path=reverse(
            "admin:export_job_progress",
            kwargs={"job_id": artist_export_job.pk},
        ),
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == artist_export_job.export_status.title()


@pytest.mark.django_db(transaction=True)
def test_export_progress_for_async_mode(
    client: Client,
    superuser: User,
    mocker: pytest_mock.MockerFixture,
):
    """Test export job admin progress page."""
    client.force_login(superuser)

    # Prepare data to imitate intermediate task state
    mocker.patch(
        "celery.result.AsyncResult.info",
        new={"current": 2, "total": 3},
    )
    expected_percent = 66
    artist_export_job = ArtistExportJobFactory()
    artist_export_job.export_status = ExportJob.ExportStatus.EXPORTING
    artist_export_job.save()

    response = client.post(
        path=reverse(
            "admin:export_job_progress",
            kwargs={"job_id": artist_export_job.pk},
        ),
    )
    assert response.status_code == status.HTTP_200_OK
    json_data = response.json()
    assert "total" in json_data
    assert "current" in json_data
    assert response.json()["percent"] == expected_percent


@pytest.mark.django_db(transaction=True)
def test_export_progress_with_deleted_export_job(
    client: Client,
    superuser: User,
    mocker: pytest_mock.MockerFixture,
):
    """Test export job admin progress page with deleted export job."""
    client.force_login(superuser)

    mocker.patch("import_export_extensions.tasks.export_data_task.apply_async")
    artist_export_job = ArtistExportJobFactory()
    job_id = artist_export_job.id
    artist_export_job.delete()

    expected_error_message = "ExportJob matching query does not exist."

    response = client.post(
        path=reverse(
            "admin:export_job_progress",
            kwargs={
                "job_id": job_id,
            },
        ),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["validation_error"] == expected_error_message


@pytest.mark.django_db(transaction=True)
def test_export_progress_with_failed_celery_task(
    client: Client,
    superuser: User,
    mocker: pytest_mock.MockerFixture,
):
    """Test export job admin progress page with deleted export job."""
    client.force_login(superuser)

    mocker.patch(
        "celery.result.AsyncResult.state",
        new=states.FAILURE,
    )
    mocker.patch(
        "celery.result.AsyncResult.info",
        new="Mocked Error Message",
    )
    artist_export_job = ArtistExportJobFactory()
    artist_export_job.export_status = ExportJob.ExportStatus.EXPORTING
    artist_export_job.save()

    response = client.post(
        path=reverse(
            "admin:export_job_progress",
            kwargs={
                "job_id": artist_export_job.id,
            },
        ),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["state"] == states.FAILURE
    artist_export_job.refresh_from_db()
    assert (
        artist_export_job.export_status == ExportJob.ExportStatus.EXPORT_ERROR
    )
