import pytest

from import_export_extensions.models import ImportJob

from ...fake_app.factories import ArtistImportJobFactory
from ...fake_app.models import Artist


@pytest.mark.django_db(transaction=True)
def test_import_data_valid_data_file(
    existing_artist: Artist,
    new_artist: Artist,
):
    """Test `import_data` with valid importing data.

    Required logic:

    * run import and update instances in DB
    * save import result to ImportJob
    * update ImportJob status

    Case is following:

    * export one artist from DB and one new (not saved) artist
    * import data

    """
    job: ImportJob = ArtistImportJobFactory(
        artists=[
            existing_artist,
            new_artist,
        ],
    )
    job.parse_data()
    job.confirm_import()
    job.refresh_from_db()

    assert job.import_status == ImportJob.ImportStatus.IMPORTED

    existing_artist_row_result = job.result.rows[0]
    new_artist_row_result = job.result.rows[1]

    # existing artist just updated
    assert not existing_artist_row_result.new_record

    # new artist added
    assert new_artist_row_result.new_record

    assert Artist.objects.count() == 2


@pytest.mark.django_db(transaction=True)
def test_job_has_finished(new_artist: Artist):
    """Tests that job `parse_finished` and `import_finished` is set.

    Attribute `parse_finished` is set then `parse` part of import job is
    completed (successfully or not). Same for `import_finished` attribute
    and `import` part of job.

    """
    job: ImportJob = ArtistImportJobFactory(artists=[new_artist])
    assert job.parse_finished is None
    assert job.import_finished is None

    job.parse_data()
    job.refresh_from_db()
    assert job.parse_finished

    job.confirm_import()
    job.refresh_from_db()
    assert job.import_finished


def test_import_data_wrong_status(artist_import_job: ImportJob):
    """Test `import_data` while job in wrong status raises ValueError."""
    artist_import_job.parse_data()
    artist_import_job.import_status = ImportJob.ImportStatus.PARSE_ERROR
    artist_import_job.save()

    with pytest.raises(
        ValueError,
        match=f"ImportJob with id {artist_import_job.id} has incorrect status",
    ):
        artist_import_job.import_data()


@pytest.mark.parametrize(
    [
        "skip_parse_step",
        "is_valid_file",
        "expected_status",
        "is_instance_created",
    ],
    [
        [False, True, ImportJob.ImportStatus.PARSED, False],
        [False, False, ImportJob.ImportStatus.INPUT_ERROR, False],
        [True, True, ImportJob.ImportStatus.IMPORTED, True],
        [True, False, ImportJob.ImportStatus.IMPORT_ERROR, False],
    ],
)
@pytest.mark.django_db(transaction=True)
def test_import_data_skip_parse_step(
    new_artist: Artist,
    skip_parse_step: bool,
    is_valid_file: bool,
    expected_status: ImportJob.ImportStatus,
    is_instance_created: bool,
):
    """Test import job skip parse step logic.

    If `skip_parse_step=True`,
    then instance will import data if no errors detected.
    If `skip_parse_step=False`, then parse only.

    """
    import_job: ImportJob = ArtistImportJobFactory.build(
        artists=[new_artist],
        force_import=False,
        skip_parse_step=skip_parse_step,
        is_valid_file=is_valid_file,
    )
    import_job.save()
    import_job.refresh_from_db()

    assert import_job.import_status == expected_status
    assert (
        Artist.objects.filter(name=new_artist.name).exists()
        == is_instance_created
    )


def test_force_import_create_correct_rows(
    new_artist: Artist,
):
    """Test import job with `force_import=True` create correct rows."""
    import_job: ImportJob = ArtistImportJobFactory(
        artists=[new_artist],
        force_import=True,
        skip_parse_step=True,
        is_valid_file=False,
    )
    import_job.import_data()
    import_job.refresh_from_db()
    assert import_job.import_status == import_job.ImportStatus.IMPORTED
    assert Artist.objects.filter(name=new_artist.name).exists()
