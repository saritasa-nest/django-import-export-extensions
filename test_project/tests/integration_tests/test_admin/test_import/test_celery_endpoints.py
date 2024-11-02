from django.contrib.auth.models import User
from django.test.client import Client
from django.urls import reverse

from rest_framework import status

import pytest
import pytest_mock

from import_export_extensions.models import ImportJob
from test_project.fake_app.factories import ArtistImportJobFactory


def test_celery_import_status_view_during_import(
    client: Client,
    superuser: User,
    mocker: pytest_mock.MockerFixture,
):
    """Test import status page when import in progress."""
    client.force_login(superuser)

    mocker.patch("import_export_extensions.tasks.parse_data_task.apply_async")
    artist_import_job = ArtistImportJobFactory(skip_parse_step=True)
    artist_import_job.import_status = ImportJob.ImportStatus.IMPORTING
    artist_import_job.save()

    response = client.get(
        path=reverse(
            "admin:fake_app_artist_import_job_status",
            kwargs={"job_id": artist_import_job.pk},
        ),
    )

    expected_import_job_url = reverse(
        "admin:import_job_progress",
        kwargs={"job_id": artist_import_job.id},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.context["import_job_url"] == expected_import_job_url


@pytest.mark.parametrize(
    argnames="incorrect_job_status",
    argvalues=[
        ImportJob.ImportStatus.CREATED,
        ImportJob.ImportStatus.PARSING,
        ImportJob.ImportStatus.PARSE_ERROR,
        ImportJob.ImportStatus.CONFIRMED,
        ImportJob.ImportStatus.IMPORTING,
        ImportJob.ImportStatus.CANCELLED,
    ],
)
def test_celery_import_results_view_redirect_to_status_page(
    client: Client,
    superuser: User,
    incorrect_job_status: ImportJob.ImportStatus,
    mocker: pytest_mock.MockerFixture,
):
    """Test redirect to import status page when job in not result status."""
    client.force_login(superuser)

    mocker.patch("import_export_extensions.tasks.parse_data_task.apply_async")
    artist_import_job = ArtistImportJobFactory()
    artist_import_job.import_status = incorrect_job_status
    artist_import_job.save()

    response = client.get(
        path=reverse(
            "admin:fake_app_artist_import_job_results",
            kwargs={"job_id": artist_import_job.pk},
        ),
    )

    expected_redirect_url = reverse(
        "admin:fake_app_artist_import_job_status",
        kwargs={"job_id": artist_import_job.pk},
    )
    assert response.status_code == status.HTTP_302_FOUND
    assert response.url == expected_redirect_url


@pytest.mark.parametrize(
    argnames="incorrect_job_status",
    argvalues=[
        ImportJob.ImportStatus.INPUT_ERROR,
        ImportJob.ImportStatus.IMPORT_ERROR,
        ImportJob.ImportStatus.IMPORTED,
    ],
)
def test_celery_import_results_confirm_forbidden(
    client: Client,
    superuser: User,
    incorrect_job_status: ImportJob.ImportStatus,
    mocker: pytest_mock.MockerFixture,
):
    """Check that confirm from result page forbidden for not PARSED jobs."""
    client.force_login(superuser)

    mocker.patch("import_export_extensions.tasks.parse_data_task.apply_async")
    artist_import_job = ArtistImportJobFactory()
    artist_import_job.import_status = incorrect_job_status
    artist_import_job.save()

    response = client.post(
        path=reverse(
            "admin:fake_app_artist_import_job_results",
            kwargs={"job_id": artist_import_job.pk},
        ),
        data={"confirm": "Confirm import"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
