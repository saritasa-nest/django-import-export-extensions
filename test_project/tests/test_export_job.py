from pytest_mock import MockerFixture

from import_export_extensions.models import ExportJob

from ..fake_app.factories import ArtistExportJobFactory


def test_export_data_exported(artist_export_job: ExportJob):
    """Test that data correctly exported and data_file exists."""
    artist_export_job.export_data()

    # ensure status updated
    assert (
        artist_export_job.export_status == ExportJob.ExportStatus.EXPORTED
    ), artist_export_job.traceback

    # ensure file exists
    assert artist_export_job.data_file


def test_export_data_error(
    artist_export_job: ExportJob,
    mocker: MockerFixture,
):
    """Test that exported with errors data has traceback and error_message."""
    mocker.patch(
        target="import_export_extensions.models.ExportJob._export_data_inner",
        side_effect=ValueError("Unknown error"),
    )

    artist_export_job.export_data()

    # ensure status updated
    assert (
        artist_export_job.export_status == ExportJob.ExportStatus.EXPORT_ERROR
    )

    # ensure traceback and message are collected
    assert artist_export_job.traceback
    assert artist_export_job.error_message


def test_job_has_finished(artist_export_job: ExportJob):
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
