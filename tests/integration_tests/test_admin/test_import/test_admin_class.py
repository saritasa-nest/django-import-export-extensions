import pytest
import pytest_mock
from django.contrib.auth.models import User
from django.test.client import Client
from django.urls import reverse

from example.app import factories
from import_export_extensions import models as ie_models


@pytest.mark.parametrize(
    argnames=["job_status", "expected_fieldsets"],
    argvalues=[
        pytest.param(
            ie_models.ImportJob.ImportStatus.CREATED,
            (),
            id="Get fieldsets for job in status CREATED",
        ),
        pytest.param(
            ie_models.ImportJob.ImportStatus.IMPORTED,
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
            ie_models.ImportJob.ImportStatus.IMPORTING,
            (
                (
                    "import_status",
                    "import_progressbar",
                ),
            ),
            id="Get fieldsets for job in status IMPORTING",
        ),
        pytest.param(
            ie_models.ImportJob.ImportStatus.IMPORT_ERROR,
            (("traceback",),),
            id="Get fieldsets for job in status IMPORT_ERROR",
        ),
    ],
)
def test_get_fieldsets_by_import_job_status(
    client: Client,
    superuser: User,
    job_status: ie_models.ImportJob.ImportStatus,
    expected_fieldsets: tuple[tuple[str]],
    mocker: pytest_mock.MockerFixture,
):
    """Test that appropriate fieldsets returned for different job statuses."""
    client.force_login(superuser)

    mocker.patch(
        "import_export_extensions.models.ImportJob.import_data",
    )
    artist_import_job = factories.ArtistImportJobFactory.create()
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
