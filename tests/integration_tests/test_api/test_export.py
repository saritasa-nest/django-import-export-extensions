import collections.abc

import pytest
import pytest_django
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status, test

from import_export_extensions import models as ie_models


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    argnames=[
        "export_url",
        "expected_resource_path",
    ],
    argvalues=[
        pytest.param(
            reverse("export-artist-start"),
            "example.app.resources.SimpleArtistResource",
            id="Export url",
        ),
        pytest.param(
            reverse("artists-export"),
            "example.app.resources.SimpleArtistResource",
            id="Action url",
        ),
        pytest.param(
            reverse("artists-export-m2m"),
            "example.app.resources.ArtistResourceWithM2M",
            id="Extra action url",
        ),
        pytest.param(
            reverse("export-band-start"),
            "example.app.resources.BandResourceWithM2M",
            id="Export url resource with no filterset",
        ),
    ],
)
def test_export_api_creates_export_job(
    admin_api_client: test.APIClient,
    export_url: str,
    expected_resource_path: str,
):
    """Ensure export start API creates new export job."""
    response = admin_api_client.post(
        path=export_url,
        data={
            "file_format": "csv",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED, response.data
    assert (
        response.data["export_status"]
        == ie_models.ExportJob.ExportStatus.CREATED
    )
    assert (
        job := ie_models.ExportJob.objects.filter(
            id=response.data["id"],
        ).first()
    )
    assert job.resource_path == expected_resource_path


def test_export_api_action_throttling(
    admin_api_client: test.APIClient,
    settings: pytest_django.fixtures.Settings,
):
    """Ensure that throttling works properly."""
    settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["export"] = "5/day"
    for _ in range(5):
        response = admin_api_client.post(
            path=reverse("artists-export-m2m"),
            data={
                "file_format": "csv",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert (
            response.data["export_status"]
            == ie_models.ExportJob.ExportStatus.CREATED
        )
        assert ie_models.ExportJob.objects.filter(
            id=response.data["id"],
        ).exists()
    response = admin_api_client.post(
        path=reverse("artists-export-m2m"),
        data={
            "file_format": "csv",
        },
    )
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS, (
        response.data
    )


@pytest.mark.parametrize(
    argnames=[
        "filter_query",
        "filter_name",
        "filter_value",
    ],
    argvalues=[
        pytest.param(
            "name=Artist",
            "name",
            "Artist",
            id="Simple str filter",
        ),
        pytest.param(
            "id=1",
            "id",
            "1",
            id="Simple int filter",
        ),
        pytest.param(
            "name__in=Some,Artist",
            "name__in",
            "Some,Artist",
            id="Simple `in` filter",
        ),
    ],
)
@pytest.mark.parametrize(
    argnames="export_url",
    argvalues=[
        pytest.param(
            reverse("export-artist-start"),
            id="Export url",
        ),
        pytest.param(
            reverse("artists-export"),
            id="Action url",
        ),
    ],
)
def test_export_api_filtering(
    admin_api_client: test.APIClient,
    filter_query: str,
    filter_name: str,
    filter_value: str,
    export_url: str,
):
    """Ensure export start API passes filter kwargs correctly."""
    response = admin_api_client.post(
        path=f"{export_url}?{filter_query}",
        data={
            "file_format": "csv",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED, response.data
    assert (
        response.data["export_status"]
        == ie_models.ExportJob.ExportStatus.CREATED
    )
    assert (
        export_job := ie_models.ExportJob.objects.filter(
            id=response.data["id"],
        ).first()
    )
    assert (
        export_job.resource_kwargs["filter_kwargs"][filter_name]
        == filter_value
    ), export_job.resource_kwargs["filter_kwargs"]


@pytest.mark.parametrize(
    argnames=[
        "ordering_query",
        "ordering_value",
    ],
    argvalues=[
        pytest.param(
            "ordering=name",
            [
                "name",
            ],
            id="One field",
        ),
        pytest.param(
            "ordering=name%2C-id",
            [
                "name",
                "-id",
            ],
            id="Many fields",
        ),
    ],
)
@pytest.mark.parametrize(
    argnames="export_url",
    argvalues=[
        pytest.param(
            reverse("export-artist-start"),
            id="Export url",
        ),
        pytest.param(
            reverse("artists-export"),
            id="Action url",
        ),
        pytest.param(
            reverse("artists-export-m2m"),
            id="Extra action url",
        ),
    ],
)
def test_export_api_ordering(
    admin_api_client: test.APIClient,
    ordering_query: str,
    ordering_value: collections.abc.Sequence[str],
    export_url: str,
):
    """Ensure export start API passes ordering correctly."""
    response = admin_api_client.post(
        path=f"{export_url}?{ordering_query}",
        data={
            "file_format": "csv",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED, response.data
    assert (
        response.data["export_status"]
        == ie_models.ExportJob.ExportStatus.CREATED
    )
    assert (
        export_job := ie_models.ExportJob.objects.filter(
            id=response.data["id"],
        ).first()
    )
    assert export_job.resource_kwargs["ordering"] == ordering_value, (
        export_job.resource_kwargs["ordering"]
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    argnames="export_url",
    argvalues=[
        pytest.param(
            f"{reverse('export-artist-start')}?id=invalid_id",
            id="Export url with invalid filter_kwargs",
        ),
        pytest.param(
            f"{reverse('artists-export')}?id=invalid_id",
            id="Action url with invalid filter_kwargs",
        ),
        pytest.param(
            f"{reverse('artists-export-m2m')}?id=invalid_id",
            id="Extra action url with invalid filter_kwargs",
        ),
    ],
)
def test_export_api_create_export_job_with_invalid_filter_kwargs(
    admin_api_client: test.APIClient,
    export_url: str,
):
    """Ensure export start API with invalid kwargs return an error."""
    response = admin_api_client.post(
        path=export_url,
        data={
            "file_format": "csv",
        },
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.data
    assert str(response.data["id"][0]) == "Enter a number."


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    argnames="export_url",
    argvalues=[
        pytest.param(
            f"{reverse('export-artist-start')}?ordering=invalid_id",
            id="Export url with invalid ordering",
        ),
        pytest.param(
            f"{reverse('artists-export')}?ordering=invalid_id",
            id="Action url with invalid ordering",
        ),
        pytest.param(
            f"{reverse('artists-export-m2m')}?ordering=invalid_id",
            id="Extra action url with invalid ordering",
        ),
    ],
)
def test_export_api_create_export_job_with_invalid_ordering(
    admin_api_client: test.APIClient,
    export_url: str,
):
    """Ensure export start API with invalid ordering return an error."""
    response = admin_api_client.post(
        path=export_url,
        data={
            "file_format": "csv",
        },
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST, response.data
    assert (
        str(response.data["ordering"][0])
        == "Cannot resolve keyword 'invalid_id' into field."
    ), response.data


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    argnames="export_url",
    argvalues=[
        pytest.param(
            "export-artist-detail",
            id="Model url",
        ),
        pytest.param(
            "export-jobs-detail",
            id="General url",
        ),
    ],
)
def test_export_api_detail(
    admin_api_client: test.APIClient,
    artist_export_job: ie_models.ExportJob,
    export_url: str,
):
    """Ensure export detail API shows current export job status."""
    response = admin_api_client.get(
        path=reverse(
            export_url,
            kwargs={"pk": artist_export_job.id},
        ),
    )
    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data["export_finished"]


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    argnames="export_url",
    argvalues=[
        pytest.param(
            "export-artist-detail",
            id="Model url",
        ),
        pytest.param(
            "export-jobs-detail",
            id="General url",
        ),
    ],
)
def test_import_user_api_get_detail(
    user: User,
    admin_api_client: test.APIClient,
    artist_export_job: ie_models.ExportJob,
    export_url: str,
):
    """Ensure import detail api for user returns only users jobs."""
    response = admin_api_client.get(
        path=reverse(
            export_url,
            kwargs={"pk": artist_export_job.id},
        ),
    )
    assert response.status_code == status.HTTP_200_OK, response.data

    artist_export_job.created_by = user
    artist_export_job.save()
    response = admin_api_client.get(
        path=reverse(
            export_url,
            kwargs={"pk": artist_export_job.id},
        ),
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND, response.data


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    argnames="allowed_cancel_status",
    argvalues=[
        ie_models.ExportJob.ExportStatus.CREATED,
        ie_models.ExportJob.ExportStatus.EXPORTING,
    ],
)
@pytest.mark.parametrize(
    argnames="export_url",
    argvalues=[
        pytest.param(
            "export-artist-cancel",
            id="Model url",
        ),
        pytest.param(
            "export-jobs-cancel",
            id="General url",
        ),
    ],
)
def test_export_api_cancel(
    admin_api_client: test.APIClient,
    artist_export_job: ie_models.ExportJob,
    allowed_cancel_status: ie_models.ExportJob.ExportStatus,
    export_url: str,
):
    """Ensure that export canceled with allowed statuses."""
    artist_export_job.export_status = allowed_cancel_status
    artist_export_job.save()
    response = admin_api_client.post(
        path=reverse(
            export_url,
            kwargs={"pk": artist_export_job.pk},
        ),
    )
    assert response.status_code == status.HTTP_200_OK, response.data
    assert (
        response.data["export_status"]
        == ie_models.ExportJob.ExportStatus.CANCELLED
    )
    assert not response.data["export_finished"]


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    argnames="incorrect_job_status",
    argvalues=[
        ie_models.ExportJob.ExportStatus.EXPORT_ERROR,
        ie_models.ExportJob.ExportStatus.EXPORTED,
        ie_models.ExportJob.ExportStatus.CANCELLED,
    ],
)
@pytest.mark.parametrize(
    argnames="export_url",
    argvalues=[
        pytest.param(
            "export-artist-cancel",
            id="Model url",
        ),
        pytest.param(
            "export-jobs-cancel",
            id="General url",
        ),
    ],
)
def test_export_api_cancel_with_errors(
    admin_api_client: test.APIClient,
    artist_export_job: ie_models.ExportJob,
    incorrect_job_status: ie_models.ExportJob.ExportStatus,
    export_url: str,
):
    """Ensure that export job with incorrect statuses cannot be canceled."""
    artist_export_job.export_status = incorrect_job_status
    artist_export_job.save()
    response = admin_api_client.post(
        path=reverse(
            export_url,
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
