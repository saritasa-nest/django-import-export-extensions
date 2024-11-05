from django.contrib.auth.models import User
from django.test.client import Client
from django.urls import reverse

from rest_framework import status

import pytest
import pytest_mock

from import_export_extensions.models import ImportJob
from test_project.fake_app.factories import ArtistImportJobFactory


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    argnames="allowed_cancel_status",
    argvalues=[
        ImportJob.ImportStatus.CREATED,
        ImportJob.ImportStatus.PARSING,
        ImportJob.ImportStatus.IMPORTING,
        ImportJob.ImportStatus.CONFIRMED,
    ],
)
def test_cancel_import_admin_action(
    client: Client,
    superuser: User,
    allowed_cancel_status: ImportJob.ImportStatus,
    mocker: pytest_mock.MockerFixture,
):
    """Test `cancel_import` via admin action."""
    client.force_login(superuser)

    revoke_mock = mocker.patch("celery.current_app.control.revoke")
    artist_import_job = ArtistImportJobFactory()
    artist_import_job.import_status = allowed_cancel_status
    artist_import_job.save()

    response = client.post(
        reverse("admin:import_export_extensions_importjob_changelist"),
        data={
            "action": "cancel_jobs",
            "_selected_action": [artist_import_job.pk],
        },
        follow=True,
    )
    artist_import_job.refresh_from_db()

    assert response.status_code == status.HTTP_200_OK
    assert artist_import_job.import_status == ImportJob.ImportStatus.CANCELLED
    assert (
        response.context["messages"]._loaded_data[0].message
        == f"Import of {artist_import_job} canceled"
    )
    revoke_mock.assert_called_once()


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    argnames="incorrect_job_status",
    argvalues=[
        ImportJob.ImportStatus.INPUT_ERROR,
        ImportJob.ImportStatus.PARSE_ERROR,
        ImportJob.ImportStatus.IMPORT_ERROR,
        ImportJob.ImportStatus.IMPORTED,
        ImportJob.ImportStatus.CANCELLED,
    ],
)
def test_cancel_import_admin_action_with_incorrect_import_job_status(
    client: Client,
    superuser: User,
    incorrect_job_status: ImportJob.ImportStatus,
    mocker: pytest_mock.MockerFixture,
):
    """Test `cancel_import` via admin action with wrong import job status."""
    client.force_login(superuser)

    revoke_mock = mocker.patch("celery.current_app.control.revoke")
    artist_import_job = ArtistImportJobFactory()
    artist_import_job.import_status = incorrect_job_status
    artist_import_job.save()

    expected_error_message = (
        f"ImportJob with id {artist_import_job.pk} has incorrect status"
    )

    response = client.post(
        reverse("admin:import_export_extensions_importjob_changelist"),
        data={
            "action": "cancel_jobs",
            "_selected_action": [artist_import_job.pk],
        },
        follow=True,
    )
    artist_import_job.refresh_from_db()

    assert response.status_code == status.HTTP_200_OK
    assert artist_import_job.import_status == incorrect_job_status
    assert (
        expected_error_message
        in response.context["messages"]._loaded_data[0].message
    )
    revoke_mock.assert_not_called()


@pytest.mark.django_db(transaction=True)
def test_confirm_import_admin_action(
    client: Client,
    superuser: User,
    mocker: pytest_mock.MockerFixture,
):
    """Test `confirm_import` via admin action."""
    client.force_login(superuser)

    import_data_mock = mocker.patch(
        "import_export_extensions.models.ImportJob.import_data",
    )
    artist_import_job = ArtistImportJobFactory()
    artist_import_job.refresh_from_db()

    response = client.post(
        reverse("admin:import_export_extensions_importjob_changelist"),
        data={
            "action": "confirm_jobs",
            "_selected_action": [artist_import_job.pk],
        },
        follow=True,
    )
    artist_import_job.refresh_from_db()

    assert response.status_code == status.HTTP_200_OK
    assert artist_import_job.import_status == ImportJob.ImportStatus.CONFIRMED
    assert (
        response.context["messages"]._loaded_data[0].message
        == f"Import of {artist_import_job} confirmed"
    )
    import_data_mock.assert_called_once()


@pytest.mark.django_db(transaction=True)
def test_confirm_import_admin_action_with_incorrect_import_job_status(
    client: Client,
    superuser: User,
):
    """Test `confirm_import` via admin action with wrong import job status."""
    client.force_login(superuser)

    artist_import_job = ArtistImportJobFactory()
    artist_import_job.import_status = ImportJob.ImportStatus.CANCELLED
    artist_import_job.save()

    expected_error_message = (
        f"ImportJob with id {artist_import_job.pk} has incorrect status"
    )

    response = client.post(
        reverse("admin:import_export_extensions_importjob_changelist"),
        data={
            "action": "confirm_jobs",
            "_selected_action": [artist_import_job.pk],
        },
        follow=True,
    )
    artist_import_job.refresh_from_db()

    assert response.status_code == status.HTTP_200_OK
    assert artist_import_job.import_status == ImportJob.ImportStatus.CANCELLED
    assert (
        expected_error_message
        in response.context["messages"]._loaded_data[0].message
    )
