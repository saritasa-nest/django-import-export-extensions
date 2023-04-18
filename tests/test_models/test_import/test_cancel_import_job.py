import pytest
from pytest_mock import MockerFixture

from import_export_extensions.models import ImportJob

from ...fake_app.factories import ArtistImportJobFactory
from ...fake_app.models import Artist


def test_cancel_import_error_status(
    existing_artist: Artist,
    new_artist: Artist,
):
    """Test `cancel_import` for import job with wrong status.

    There should be raised `ValueError` when status of BaseImportJob is
    incorrect.

    """
    job: ImportJob = ArtistImportJobFactory(
        artists=[existing_artist, new_artist],
    )
    job.import_status = ImportJob.ImportStatus.PARSED
    with pytest.raises(ValueError, match="Wrong import job status"):
        job.cancel_import()


def test_cancel_import_success_status(
    existing_artist: Artist,
    new_artist: Artist,
):
    """Test `cancel_import` for import job with success status.

    No error should be raised and ImportJob `status` should be updated to
    cancelled.

    """
    job: ImportJob = ArtistImportJobFactory(
        artists=[existing_artist, new_artist],
    )
    job.cancel_import()
    assert job.import_status == ImportJob.ImportStatus.CANCELLED


def test_cancel_import_with_celery_parse_task_id(
    existing_artist: Artist,
    new_artist: Artist,
    mocker: MockerFixture,
):
    """Test `cancel_import` for import job with celery.

    When celery is used -> there should be called celery task `revoke` with
    terminating and correct `task_id`.

    """
    revoke = mocker.patch("celery.current_app.control.revoke")
    job: ImportJob = ArtistImportJobFactory(
        artists=[existing_artist, new_artist],
    )
    job.cancel_import()

    assert job.import_status == ImportJob.ImportStatus.CANCELLED

    revoke.assert_called_with(job.parse_task_id, terminate=True)


def test_cancel_import_with_celery_import_task_id(
    existing_artist: Artist,
    new_artist: Artist,
    mocker: MockerFixture,
):
    """Test `cancel_import` for import job with celery.

    When celery is used -> there should be called celery task `revoke` with
    terminating and correct `task_id`.

    """
    revoke = mocker.patch("celery.current_app.control.revoke")
    job: ImportJob = ArtistImportJobFactory(
        artists=[existing_artist, new_artist],
    )
    job.parse_data()
    job.confirm_import()
    job.cancel_import()
    assert job.import_status == ImportJob.ImportStatus.CANCELLED
    revoke.assert_called_with(job.import_task_id, terminate=True)


@pytest.mark.django_db(transaction=True)
def test_cancel_import_with_custom_task_id_on_parse(
    existing_artist: Artist,
    new_artist: Artist,
    mocker: MockerFixture,
):
    """Test `cancel_import` on parsing data with custom celery task_id.

    Check that when new ImportJob is created there would be called a
    `parse_data` method with auto generated `task_id`.

    """
    parse_data = mocker.patch(
        "import_export_extensions.models.ImportJob.parse_data",
    )
    job: ImportJob = ArtistImportJobFactory(
        artists=[existing_artist, new_artist],
    )
    job.cancel_import()

    assert job.import_status == ImportJob.ImportStatus.CANCELLED

    parse_data.assert_called_once()


@pytest.mark.django_db(transaction=True)
def test_cancel_import_with_custom_task_id_on_import(
    existing_artist: Artist,
    new_artist: Artist,
    mocker: MockerFixture,
):
    """Test `cancel_import` on importing data with custom celery task_id.

    Check that when data for ImportJob is imported there would be called a
    `confirm_import` method with auto generated `task_id`.

    """
    import_data = mocker.patch(
        "import_export_extensions.models.ImportJob.import_data",
    )
    job: ImportJob = ArtistImportJobFactory(
        artists=[existing_artist, new_artist],
    )
    job.parse_data()
    job.confirm_import()
    job.cancel_import()
    assert job.import_status == ImportJob.ImportStatus.CANCELLED

    import_data.assert_called_once()
