from django.contrib.auth.models import User
from django.test.client import Client
from django.urls import reverse

from rest_framework import status

import pytest
import pytest_mock

from import_export_extensions.models import ExportJob
from test_project.fake_app.factories import ArtistExportJobFactory


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
