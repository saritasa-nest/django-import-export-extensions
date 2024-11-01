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
    assert response.status_code == status.HTTP_201_CREATED, response.data
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
    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.data
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
    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data["export_finished"]


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    argnames="allowed_cancel_status",
    argvalues=[
        ExportJob.ExportStatus.CREATED,
        ExportJob.ExportStatus.EXPORTING,
    ],
)
def test_export_api_cancel(
    admin_api_client: test.APIClient,
    artist_export_job: ExportJob,
    allowed_cancel_status: ExportJob.ExportStatus,
):
    """Ensure that export canceled with allowed statuses."""
    artist_export_job.export_status = allowed_cancel_status
    artist_export_job.save()
    response = admin_api_client.post(
        path=reverse(
            "export-artist-cancel",
            kwargs={"pk": artist_export_job.pk},
        ),
    )
    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data["export_status"] == ExportJob.ExportStatus.CANCELLED
    assert not response.data["export_finished"]


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    argnames="incorrect_job_status",
    argvalues=[
        ExportJob.ExportStatus.EXPORT_ERROR,
        ExportJob.ExportStatus.EXPORTED,
        ExportJob.ExportStatus.CANCELLED,
    ],
)
def test_export_api_cancel_with_errors(
    admin_api_client: test.APIClient,
    artist_export_job: ExportJob,
    incorrect_job_status: ExportJob.ExportStatus,
):
    """Ensure that export job with incorrect statuses cannot be canceled."""
    artist_export_job.export_status = incorrect_job_status
    artist_export_job.save()
    response = admin_api_client.post(
        path=reverse(
            "export-artist-cancel",
            kwargs={"pk": artist_export_job.pk},
        ),
    )
    expected_error_message = (
        f"ExportJob with id {artist_export_job.pk} has incorrect status: "
        f"`{incorrect_job_status.value}`. Expected statuses: "
        "['CREATED', 'EXPORTING']"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.data
    assert str(response.data[0]) == expected_error_message
