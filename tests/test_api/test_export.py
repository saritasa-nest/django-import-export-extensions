from django.urls import reverse

from rest_framework import status, test

import pytest

from import_export_extensions.models import ExportJob


@pytest.mark.django_db(transaction=True)
def test_export_api_creates_export_job(admin_api_client: test.APIClient):
    """Ensure export start API creates new export job."""
    response = admin_api_client.post(
        path=reverse("export-artist-start"),
        data={
            "file_format": "csv",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["export_status"] == "CREATED"
    assert ExportJob.objects.first()


@pytest.mark.django_db(transaction=True)
def test_export_api_detail(
    admin_api_client: test.APIClient,
    artist_export_job: ExportJob,
):
    """Ensure export detail API shows current export job status."""
    response = admin_api_client.get(
        path=reverse(
            "export-artist-detail",
            kwargs={"pk": artist_export_job.id},
        ),
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["export_finished"]
