from django.contrib.auth.models import User
from django.test.client import Client
from django.urls import reverse

import pytest
import pytest_mock

from import_export_extensions.models import ExportJob
from test_project.fake_app.factories import ArtistExportJobFactory


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
    job = ArtistExportJobFactory.create()
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
