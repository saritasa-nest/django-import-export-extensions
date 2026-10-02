import pytest
import pytest_django
import pytest_mock
import tablib
from import_export import results

from import_export_extensions import models

from ..fake_app.factories import ArtistExportJobFactory


@pytest.mark.parametrize(
    argnames="save_result_enabled",
    argvalues=[
        pytest.param(True, id="enabled"),
        pytest.param(False, id="disabled"),
    ],
)
def test_export_data_exported(
    save_result_enabled: bool,
    artist_export_job: models.ExportJob,
    settings: pytest_django.fixtures.Settings,
):
    """Test that data correctly exported and data_file exists."""
    settings.EXPORT_SAVE_RESULT_OBJ = save_result_enabled
    artist_export_job.export_data()

    # ensure status updated
    assert (
        artist_export_job.export_status
        == models.ExportJob.ExportStatus.EXPORTED
    ), artist_export_job.traceback

    # check result obj
    if save_result_enabled:
        assert isinstance(artist_export_job.result, tablib.Dataset), (
            artist_export_job.result
        )
    else:
        assert isinstance(artist_export_job.result, results.Result), (
            artist_export_job.result
        )
    # ensure file exists
    assert artist_export_job.data_file


def test_export_data_error(
    artist_export_job: models.ExportJob,
    mocker: pytest_mock.MockerFixture,
):
    """Test that exported with errors data has traceback and error_message."""
    mocker.patch(
        target="import_export_extensions.models.ExportJob._export_data_inner",
        side_effect=ValueError("Unknown error"),
    )

    artist_export_job.export_data()

    # ensure status updated
    assert (
        artist_export_job.export_status
        == models.ExportJob.ExportStatus.EXPORT_ERROR
    )

    # ensure traceback and message are collected
    assert artist_export_job.traceback
    assert artist_export_job.error_message


def test_job_has_finished(artist_export_job: models.ExportJob):
    """Test that job `finished` field is set.

    Attribute `finished` is set then export job is completed
    (successfully or not).

    """
    assert not artist_export_job.export_finished

    artist_export_job.export_data()

    assert artist_export_job.export_finished


def test_export_filename_truncate():
    """Test filename is truncated by ExportJob itself."""
    job = ArtistExportJobFactory.build()

    # no error should be raised
    job.save()

    assert job.export_filename.endswith(".csv")
