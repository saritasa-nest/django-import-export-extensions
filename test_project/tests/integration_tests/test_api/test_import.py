from django.contrib.auth.models import User
from django.core.files import base as django_files
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from import_export_extensions.models.import_job import ImportJob
from test_project.fake_app.factories import ArtistImportJobFactory
from test_project.fake_app.models import Artist


@pytest.mark.django_db(transaction=True)
def test_import_api_creates_import_job(
    admin_api_client: APIClient,
    uploaded_file: SimpleUploadedFile,
):
    """Ensure import start api creates new import job."""
    import_job_count = ImportJob.objects.count()
    response = admin_api_client.post(
        path=reverse("import-artist-start"),
        data={
            "file": uploaded_file,
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["import_status"] == "CREATED"
    assert ImportJob.objects.count() == import_job_count + 1


@pytest.mark.django_db(transaction=True)
def test_import_api_detail(
    admin_api_client: APIClient,
    artist_import_job: ImportJob,
):
    """Ensure import detail api shows current import job status."""
    response = admin_api_client.get(
        path=reverse(
            "import-artist-detail",
            kwargs={"pk": artist_import_job.id},
        ),
    )
    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data["import_status"] == ImportJob.ImportStatus.PARSED

    artist_import_job.refresh_from_db()
    artist_import_job.confirm_import()

    response = admin_api_client.get(
        path=reverse(
            "import-artist-detail",
            kwargs={"pk": artist_import_job.id},
        ),
    )
    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data["import_finished"]


@pytest.mark.django_db(transaction=True)
def test_force_import_api_detail(
    admin_api_client: APIClient,
    superuser: User,
    force_import_artist_job: ImportJob,
):
    """Test detail api for force import job.

    Ensure created import job with invalid file will have `PARSED` status.
    Ensure force import job after confirmation will skip invalid rows
    and create right ones.

    """
    response = admin_api_client.get(
        path=reverse(
            "import-artist-detail",
            kwargs={"pk": force_import_artist_job.id},
        ),
    )
    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data["import_status"] == ImportJob.ImportStatus.PARSED

    force_import_artist_job.refresh_from_db()
    force_import_artist_job.confirm_import()

    response = admin_api_client.get(
        path=reverse(
            "import-artist-detail",
            kwargs={"pk": force_import_artist_job.id},
        ),
    )
    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data["import_finished"]

    force_import_artist_job.refresh_from_db()
    assert force_import_artist_job.result.totals["new"] == 1
    assert force_import_artist_job.result.totals["skip"] == 1


@pytest.mark.django_db(transaction=True)
def test_import_api_detail_with_row_errors(
    admin_api_client: APIClient,
    existing_artist: Artist,
):
    """Ensure import detail api shows row errors."""
    expected_error_message = "Instrument matching query does not exist."
    invalid_row_values = [
        str(existing_artist.id),
        existing_artist.external_id,
        existing_artist.name,
        str(existing_artist.instrument_id),
    ]

    import_artist_job = ArtistImportJobFactory(
        artists=[existing_artist],
    )
    # Remove instrument to trigger row error
    existing_artist.instrument.delete()
    import_artist_job.parse_data()

    response = admin_api_client.get(
        path=reverse(
            "import-artist-detail",
            kwargs={"pk": import_artist_job.id},
        ),
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data["import_status"] == ImportJob.ImportStatus.INPUT_ERROR
    row_error = response.data["input_error"]["row_errors"][0][0]
    assert row_error["line"] == 1
    assert row_error["error"] == expected_error_message
    assert row_error["row"] == invalid_row_values


@pytest.mark.django_db(transaction=True)
def test_import_api_detail_with_base_errors(
    admin_api_client: APIClient,
    existing_artist: Artist,
):
    """Ensure import detail api shows base errors."""
    expected_error_message = (
        "The following fields are declared in 'import_id_fields' but are not "
        "present in the file headers: external_id"
    )

    # Create file with missing external_id header
    file_content = django_files.ContentFile(
        "id,name,instrument\n"
        f"{existing_artist.id},{existing_artist.name},"
        f"{existing_artist.instrument_id}\n",
    )
    uploaded_file = django_files.File(file_content.file, "data.csv")

    import_artist_job = ArtistImportJobFactory(
        artists=[existing_artist],
        data_file=uploaded_file,
        force_import=True,
    )
    import_artist_job.parse_data()

    response = admin_api_client.get(
        path=reverse(
            "import-artist-detail",
            kwargs={"pk": import_artist_job.id},
        ),
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data["import_status"] == ImportJob.ImportStatus.INPUT_ERROR
    assert (
        response.data["input_error"]["base_errors"][0]
        == expected_error_message
    )
