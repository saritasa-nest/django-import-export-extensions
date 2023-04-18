from django.contrib.auth.models import User
from django.test.client import Client
from django.urls import reverse

import pytest

from import_export_extensions.models import ExportJob


@pytest.mark.django_db(transaction=True)
def test_export_api_creates_export_job(client: Client, superuser: User):
    """Ensure export start API creates new export job."""
    client.force_login(superuser)

    response = client.post(
        path=reverse("export-artist-start"),
        data={
            "file_format": "csv",
        },
    )
    assert response.data["export_status"] == "CREATED"
    assert ExportJob.objects.first()


@pytest.mark.django_db(transaction=True)
def test_export_api_detail(
    client: Client,
    artist_export_job: ExportJob,
    superuser: User,
):
    """Ensure export detail API shows current export job status."""
    client.force_login(superuser)

    response = client.get(
        path=reverse(
            "export-artist-detail",
            kwargs={"pk": artist_export_job.id},
        ),
    )

    assert response.data["export_finished"]
