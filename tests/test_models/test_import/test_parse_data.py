import pytest
from pytest_mock import MockerFixture

from import_export_extensions.models import ImportJob


def test_parse_valid_data_file(artist_import_job: ImportJob):
    """Test `parse_data` with valid importing data.

    Required logic:

    * run import with `dry_run` (i.e. without saving new instances to DB),
    * save import result to BaseImportJob
    * update BaseImportJob status

    """
    artist_import_job.parse_data()

    # ensure status updated
    assert artist_import_job.import_status == ImportJob.ImportStatus.PARSED

    # ensure data contain no errors
    assert not artist_import_job.result.has_errors()

    # artist instance should be updated
    row_result = artist_import_job.result.rows[0]
    assert not row_result.new_record


def test_parse_data_import_errors(
    artist_import_job: ImportJob,
    mocker: MockerFixture,
):
    """Test `parse_data` with errors in input data.

    Required logic:

    * run import with `dry_run` (i.e. without saving new instances to DB),
    * save import result to BaseImportJob
    * update BaseImportJob status

    For example, some field contain invalid data

    """
    mocker.patch(
        target="tests.fake_app.resources.SimpleArtistResource.import_field",
        side_effect=ValueError("Invalid data"),
    )

    artist_import_job.parse_data()
    artist_import_job.refresh_from_db()

    # ensure status updated
    assert (
        artist_import_job.import_status == ImportJob.ImportStatus.INPUT_ERROR
    )

    # ensure job result contain explanation about errors
    assert artist_import_job.result.has_validation_errors()

    # get error of first row
    error = artist_import_job.result.invalid_rows[0].error
    assert error.messages[0] == "Invalid data"


def test_parse_data_unknown_error(
    artist_import_job: ImportJob,
    mocker: MockerFixture,
):
    """Test `parse_data` with errors during import.

    Required logic:
    * try to run import with `dry_run`
    * Some error occured (not related to iput file) (for example, broken
        file)
    * collect traceback
    * update BaseImportJob status (error on data parsing)

    For example, this may happen if data_file have wrong format

    """
    mocker.patch(
        target="import_export_extensions.models.ImportJob._parse_data_inner",
        side_effect=ValueError("Unknown error"),
    )

    artist_import_job.parse_data()

    # ensure status updated
    assert (
        artist_import_job.import_status == ImportJob.ImportStatus.PARSE_ERROR
    )

    # ensure traceback and message are collected
    assert artist_import_job.traceback
    assert artist_import_job.error_message


def test_parse_data_wrong_status(artist_import_job: ImportJob):
    """Test `parse_data` while job in wrong status raises ValueError."""
    artist_import_job.import_status = ImportJob.ImportStatus.IMPORTED
    artist_import_job.save()
    with pytest.raises(
        ValueError,
        match=f"ImportJob with id {artist_import_job.id} has incorrect status",
    ):
        artist_import_job.parse_data()


def test_error_message_length(
    artist_import_job: ImportJob,
    mocker: MockerFixture,
):
    """Test for long error_message.

    Check that there is no exception by passing error that is longer
    than 128 symbols.

    """
    max_length = 128
    mocker.patch.object(
        target=ImportJob,
        attribute="_parse_data_inner",
        side_effect=Exception("a" * (max_length + 1)),
    )
    artist_import_job.parse_data()

    assert len(artist_import_job.error_message) == max_length
