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
def test_export_progress_during_export(
    client: Client,
    superuser: User,
    mocker: pytest_mock.MockerFixture,
):
    """Test export job admin progress page during export."""
    client.force_login(superuser)

    # Prepare data to imitate intermediate task state
    fake_progress_info = {
        "current": 2,
        "total": 3,
    }
    mocker.patch(
        "celery.result.AsyncResult.info",
        new=fake_progress_info,
    )
    expected_percent = int(
        fake_progress_info["current"] / fake_progress_info["total"] * 100,
    )

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

    assert json_data == {
        "status": ExportJob.ExportStatus.EXPORTING.title(),
        "state": "SUCCESS",
        "percent": expected_percent,
        **fake_progress_info,
    }


@pytest.mark.django_db(transaction=True)
def test_export_progress_after_complete_export(
    client: Client,
    superuser: User,
):
    """Test export job admin progress page after complete export."""
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
    assert response.json() == {
        "status": artist_export_job.export_status.title(),
    }


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

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["validation_error"] == expected_error_message


@pytest.mark.django_db(transaction=True)
def test_export_progress_with_failed_celery_task(
    client: Client,
    superuser: User,
    mocker: pytest_mock.MockerFixture,
):
    """Test than after celery fail ExportJob will be in export error status."""
    client.force_login(superuser)

    expected_error_message = "Mocked Error Message"
    mocker.patch(
        "celery.result.AsyncResult.state",
        new=states.FAILURE,
    )
    mocker.patch(
        "celery.result.AsyncResult.info",
        new=ValueError(expected_error_message),
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


@pytest.mark.django_db(transaction=True)
def test_cancel_export_admin_action(
    client: Client,
    superuser: User,
    mocker: pytest_mock.MockerFixture,
):
    """Test `cancel_export` via admin action."""
    client.force_login(superuser)

    revoke_mock = mocker.patch("celery.current_app.control.revoke")
    export_data_mock = mocker.patch(
        "import_export_extensions.models.ExportJob.export_data",
    )
    job: ExportJob = ArtistExportJobFactory()

    response = client.post(
        reverse("admin:import_export_extensions_exportjob_changelist"),
        data={
            "action": "cancel_jobs",
            "_selected_action": [job.pk],
        },
        follow=True,
    )
    job.refresh_from_db()

    assert response.status_code == status.HTTP_200_OK
    assert job.export_status == ExportJob.ExportStatus.CANCELLED
    assert (
        response.context["messages"]._loaded_data[0].message
        == f"Export of {job} canceled"
    )
    export_data_mock.assert_called_once()
    revoke_mock.assert_called_once_with(job.export_task_id, terminate=True)


@pytest.mark.django_db(transaction=True)
def test_cancel_export_admin_action_with_incorrect_export_job_status(
    client: Client,
    superuser: User,
    mocker: pytest_mock.MockerFixture,
):
    """Test `cancel_export` via admin action with wrong export job status."""
    client.force_login(superuser)

    revoke_mock = mocker.patch("celery.current_app.control.revoke")
    job: ExportJob = ArtistExportJobFactory()

    expected_error_message = f"ExportJob with id {job.pk} has incorrect status"

    response = client.post(
        reverse("admin:import_export_extensions_exportjob_changelist"),
        data={
            "action": "cancel_jobs",
            "_selected_action": [job.pk],
        },
        follow=True,
    )
    job.refresh_from_db()

    assert response.status_code == status.HTTP_200_OK
    assert job.export_status == ExportJob.ExportStatus.EXPORTED
    assert (
        expected_error_message
        in response.context["messages"]._loaded_data[0].message
    )
    revoke_mock.assert_not_called()


@pytest.mark.parametrize(
    argnames=["job_status", "expected_fieldsets"],
    argvalues=[
        pytest.param(
            ExportJob.ExportStatus.CREATED,
            (
                (
                    "export_status",
                    "_model",
                    "created",
                    "export_started",
                    "export_finished",
                ),
            ),
            id="Get fieldsets for job in status CREATED",
        ),
        pytest.param(
            ExportJob.ExportStatus.EXPORTED,
            (
                (
                    "export_status",
                    "_model",
                    "created",
                    "export_started",
                    "export_finished",
                ),
                ("data_file",),
            ),
            id="Get fieldsets for job in status EXPORTED",
        ),
        pytest.param(
            ExportJob.ExportStatus.EXPORTING,
            (
                (
                    "export_status",
                    "export_progressbar",
                ),
            ),
            id="Get fieldsets for job in status EXPORTING",
        ),
        pytest.param(
            ExportJob.ExportStatus.EXPORT_ERROR,
            (
                (
                    "export_status",
                    "_model",
                    "created",
                    "export_started",
                    "export_finished",
                ),
                (
                    "error_message",
                    "traceback",
                ),
            ),
            id="Get fieldsets for job in status EXPORT_ERROR",
        ),
    ],
)
def test_get_fieldsets_by_export_job_status(
    client: Client,
    superuser: User,
    job_status: ExportJob.ExportStatus,
    expected_fieldsets: tuple[tuple[str]],
    mocker: pytest_mock.MockerFixture,
):
    """Test that appropriate fieldsets returned for different job statuses."""
    client.force_login(superuser)

    mocker.patch(
        "import_export_extensions.models.ExportJob.export_data",
    )
    job: ExportJob = ArtistExportJobFactory()
    job.export_status = job_status
    job.save()

    response = client.get(
        reverse(
            "admin:import_export_extensions_exportjob_change",
            kwargs={"object_id": job.pk},
        ),
    )

    fieldsets = response.context["adminform"].fieldsets
    fields = [fields["fields"] for _, fields in fieldsets]

    assert tuple(fields) == (
        *expected_fieldsets,
        (
            "resource_path",
            "resource_kwargs",
            "file_format_path",
        ),
    )
