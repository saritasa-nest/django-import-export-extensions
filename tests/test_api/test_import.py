from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.client import Client
from django.urls import reverse

from rest_framework import status

import pytest

from import_export_extensions.models.import_job import ImportJob


@pytest.mark.django_db(transaction=True)
def test_import_api_creates_import_job(
    client: Client,
    superuser: User,
    uploaded_file: SimpleUploadedFile,
):
    """Ensure import start api creates new import job."""
    client.force_login(superuser)
    response = client.post(
        path=reverse("import-artist-start"),
        data={
            "file": uploaded_file,
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["import_status"] == "CREATED"
    assert ImportJob.objects.first()


@pytest.mark.django_db(transaction=True)
def test_import_api_detail(
    client: Client,
    superuser: User,
    artist_import_job: ImportJob,
):
    """Ensure import detail api shows current import job status."""
    client.force_login(superuser)
    response = client.get(
        path=reverse(
            "import-artist-detail",
            kwargs={"pk": artist_import_job.id},
        ),
    )
    assert response.data["import_status"] == ImportJob.ImportStatus.PARSED

    artist_import_job.refresh_from_db()
    artist_import_job.confirm_import()

    response = client.get(
        path=reverse(
            "import-artist-detail",
            kwargs={"pk": artist_import_job.id},
        ),
    )
    assert response.data["import_finished"]
