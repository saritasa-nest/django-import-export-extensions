from django.contrib.auth.models import User
from django.test.client import Client
from django.urls import reverse

import pytest
import pytest_mock

from import_export_extensions.models import ImportJob
from test_project.fake_app.factories import ArtistImportJobFactory


@pytest.mark.parametrize(
    argnames=["job_status", "expected_fieldsets"],
    argvalues=[
        pytest.param(
            ImportJob.ImportStatus.CREATED,
            (),
            id="Get fieldsets for job in status CREATED",
        ),
        pytest.param(
            ImportJob.ImportStatus.IMPORTED,
            (
                ("_show_results",),
                (
                    "input_errors_file",
                    "_input_errors",
                ),
            ),
            id="Get fieldsets for job in status IMPORTED",
        ),
        pytest.param(
            ImportJob.ImportStatus.IMPORTING,
            (
                (
                    "import_status",
                    "import_progressbar",
                ),
            ),
            id="Get fieldsets for job in status IMPORTING",
        ),
        pytest.param(
            ImportJob.ImportStatus.IMPORT_ERROR,
            (("traceback",),),
            id="Get fieldsets for job in status IMPORT_ERROR",
        ),
    ],
)
def test_get_fieldsets_by_import_job_status(
    client: Client,
    superuser: User,
    job_status: ImportJob.ImportStatus,
    expected_fieldsets: tuple[tuple[str]],
    mocker: pytest_mock.MockerFixture,
):
    """Test that appropriate fieldsets returned for different job statuses."""
    client.force_login(superuser)

    mocker.patch(
        "import_export_extensions.models.ImportJob.import_data",
    )
    artist_import_job = ArtistImportJobFactory()
    artist_import_job.import_status = job_status
    artist_import_job.save()

    response = client.get(
        reverse(
            "admin:import_export_extensions_importjob_change",
            kwargs={"object_id": artist_import_job.pk},
        ),
    )

    fieldsets = response.context["adminform"].fieldsets
    fields = [fields["fields"] for _, fields in fieldsets]

    assert tuple(fields) == (
        (
            "import_status",
            "_model",
            "created_by",
            "created",
            "parse_finished",
            "import_started",
            "import_finished",
        ),
        *expected_fieldsets,
        (
            "data_file",
            "resource_path",
            "resource_kwargs",
        ),
    )
