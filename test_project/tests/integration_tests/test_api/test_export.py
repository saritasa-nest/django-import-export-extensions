from django.urls import reverse

from rest_framework import status, test

import pytest

from import_export_extensions.models import ExportJob


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    argnames=["export_url"],
    argvalues=[
        pytest.param(
            reverse("export-artist-start"),
            id="Url without filter_kwargs",
        ),
        pytest.param(
            f"{reverse('export-artist-start')}?name=Artist",
            id="Url with valid filter_kwargs",
        ),
    ],
)
def test_export_api_creates_export_job(
    admin_api_client: test.APIClient,
    export_url: str,
):
    """Ensure export start API creates new export job."""
    response = admin_api_client.post(
        path=export_url,
        data={
            "file_format": "csv",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["export_status"] == ExportJob.ExportStatus.CREATED
    assert ExportJob.objects.filter(id=response.data["id"]).exists()


@pytest.mark.django_db(transaction=True)
def test_export_api_create_export_job_with_invalid_filter_kwargs(
    admin_api_client: test.APIClient,
):
    """Ensure export start API with invalid kwargs return an error."""
    response = admin_api_client.post(
        path=f"{reverse('export-artist-start')}?id=invalid_id",
        data={
            "file_format": "csv",
        },
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert str(response.data["id"][0]) == "Enter a number."


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
