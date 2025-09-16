import csv
import pathlib
import uuid

import django.test
from django.contrib.auth.models import User
from django.test.client import Client
from django.urls import reverse

from rest_framework import status

import pytest
import pytest_mock
from celery import states
from pytest_lazy_fixtures import lf

from import_export_extensions.models import ExportJob
from test_project.fake_app.factories import (
    ArtistExportJobFactory,
    ArtistFactory,
)
from test_project.fake_app.models import Instrument


@pytest.mark.usefixtures("existing_artist")
@pytest.mark.django_db(transaction=True)
def test_export_using_admin_model(client: Client, superuser: User):
    """Test entire exporting process using Django Admin.

    There is following workflow:
        1. Go to Artist Export page
        2. Start Export Job with chosen file format (csv)
        3. Redirect to export job result page through the status page

    """
    client.force_login(superuser)

    # Make get request to admin export page
    export_get_response = client.get(
        path=reverse("admin:fake_app_artist_export"),
    )
    assert export_get_response.status_code == status.HTTP_200_OK

    # Start export job using admin panel
    start_export_response = client.post(
        path=reverse("admin:fake_app_artist_export"),
        data={
            "format": 0,
            "artistresourcewithm2m_id": "on",
            "artistresourcewithm2m_name": "on",
            "artistresourcewithm2m_bands": "on",
            "artistresourcewithm2m_instrument": "on",
        },
    )
    assert start_export_response.status_code == status.HTTP_302_FOUND

    # Go to redirected page after export is finished
    status_response = client.get(start_export_response.url)
    assert status_response.status_code == status.HTTP_302_FOUND

    result_response = client.get(status_response.url)
    assert result_response.status_code == status.HTTP_200_OK

    assert ExportJob.objects.exists()
    export_job = ExportJob.objects.first()
    assert export_job.export_status == ExportJob.ExportStatus.EXPORTED, (
        export_job.traceback
    )


@pytest.mark.usefixtures("existing_artist")
@pytest.mark.django_db(transaction=True)
def test_export_using_admin_with_select_fields(
    client: Client,
    superuser: User,
):
    """Test that only selected fields are exported."""
    client.force_login(superuser)

    # Make get request to admin export page
    export_get_response = client.get(
        path=reverse("admin:fake_app_artist_export"),
    )
    assert export_get_response.status_code == status.HTTP_200_OK

    response = client.post(
        path=reverse("admin:fake_app_artist_export"),
        follow=True,
        data={
            "format": 0,
            "artistresourcewithm2m_id": "on",
            "artistresourcewithm2m_name": "on",
            "artistresourcewithm2m_bands": "on",
        },
    )
    assert response.status_code == status.HTTP_200_OK

    with pathlib.Path(
        response.context["export_job"].data_file.path,
    ).open() as file:
        content = list(csv.reader(file))

    expected_fields_count = 3
    content_headers = content[0]
    exported_artist = content[1]
    assert len(content_headers) == expected_fields_count
    assert len(exported_artist) == expected_fields_count
    assert "instrument" not in content_headers


@pytest.mark.parametrize(
    argnames=["view_name", "path_kwargs"],
    argvalues=[
        pytest.param(
            "admin:fake_app_artist_export",
            None,
            id="Test access to `celery_export_action`",
        ),
        pytest.param(
            "admin:fake_app_artist_export_job_status",
            {"job_id": lf("artist_export_job.pk")},
            id="Test access to `export_job_status_view`",
        ),
        pytest.param(
            "admin:fake_app_artist_export_job_results",
            {"job_id": lf("artist_export_job.pk")},
            id="Test access to `export_job_results_view`",
        ),
    ],
)
def test_export_using_admin_model_without_permissions(
    client: Client,
    superuser: User,
    view_name: str,
    path_kwargs: dict[str, str],
    mocker: pytest_mock.MockerFixture,
):
    """Test access to celery-export endpoints forbidden without permission."""
    client.force_login(superuser)
    mocker.patch(
        "test_project.fake_app.admin.ArtistAdmin.has_export_permission",
        return_value=False,
    )

    response = client.get(
        path=reverse(
            view_name,
            kwargs=path_kwargs,
        ),
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db(transaction=True)
def test_export_progress_during_export(
    client: Client,
    superuser: User,
    mocker: pytest_mock.MockerFixture,
):
    """Test export job admin progress page during export."""
    client.force_login(superuser)

    # Prepare data to imitate intermediate task state
    fake_progress_info = {
        "current": 2,
        "total": 3,
    }
    mocker.patch(
        "celery.result.AsyncResult.info",
        new=fake_progress_info,
    )
    expected_percent = int(
        fake_progress_info["current"] / fake_progress_info["total"] * 100,
    )

    artist_export_job = ArtistExportJobFactory()
    artist_export_job.export_status = ExportJob.ExportStatus.EXPORTING
    artist_export_job.save()

    response = client.post(
        path=reverse(
            "admin:export_job_progress",
            kwargs={"job_id": artist_export_job.pk},
        ),
    )
    assert response.status_code == status.HTTP_200_OK
    json_data = response.json()

    assert json_data == {
        "status": ExportJob.ExportStatus.EXPORTING.title(),
        "state": "SUCCESS",
        "percent": expected_percent,
        **fake_progress_info,
    }


@pytest.mark.django_db(transaction=True)
def test_export_progress_after_complete_export(
    client: Client,
    superuser: User,
):
    """Test export job admin progress page after complete export."""
    client.force_login(superuser)

    artist_export_job = ArtistExportJobFactory()
    artist_export_job.refresh_from_db()

    response = client.post(
        path=reverse(
            "admin:export_job_progress",
            kwargs={"job_id": artist_export_job.pk},
        ),
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status": artist_export_job.export_status.title(),
    }


@pytest.mark.django_db(transaction=True)
def test_export_progress_with_deleted_export_job(
    client: Client,
    superuser: User,
    mocker: pytest_mock.MockerFixture,
):
    """Test export job admin progress page with deleted export job."""
    client.force_login(superuser)

    mocker.patch("import_export_extensions.tasks.export_data_task.apply_async")
    artist_export_job = ArtistExportJobFactory()
    job_id = artist_export_job.id
    artist_export_job.delete()

    expected_error_message = "ExportJob matching query does not exist."

    response = client.post(
        path=reverse(
            "admin:export_job_progress",
            kwargs={
                "job_id": job_id,
            },
        ),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["validation_error"] == expected_error_message


@pytest.mark.django_db(transaction=True)
def test_export_progress_with_failed_celery_task(
    client: Client,
    superuser: User,
    mocker: pytest_mock.MockerFixture,
):
    """Test that after celery fail ExportJob will be in export error status."""
    client.force_login(superuser)

    expected_error_message = "Mocked Error Message"
    mocker.patch(
        "celery.result.AsyncResult.state",
        new=states.FAILURE,
    )
    mocker.patch(
        "celery.result.AsyncResult.info",
        new=ValueError(expected_error_message),
    )
    artist_export_job = ArtistExportJobFactory()
    artist_export_job.export_status = ExportJob.ExportStatus.EXPORTING
    artist_export_job.save()

    response = client.post(
        path=reverse(
            "admin:export_job_progress",
            kwargs={
                "job_id": artist_export_job.id,
            },
        ),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["state"] == states.FAILURE
    artist_export_job.refresh_from_db()
    assert (
        artist_export_job.export_status == ExportJob.ExportStatus.EXPORT_ERROR
    )


@pytest.mark.django_db(transaction=True)
def test_export_using_get_params(
    client: Client,
    superuser: User,
):
    """Test export by using get params."""
    client.force_login(superuser)

    search_value = uuid.uuid4().hex
    instrument_title = uuid.uuid4().hex
    ArtistFactory.create(
        name=search_value,
        instrument__title=instrument_title,
    )
    ArtistFactory.create()
    response = client.post(
        reverse("admin:fake_app_artist_export"),
        data={
            "format": 0,
            "artistresourcewithm2m_id": "on",
            "artistresourcewithm2m_name": "on",
            "artistresourcewithm2m_bands": "on",
            "artistresourcewithm2m_instrument": "on",
        },
        follow=True,
        QUERY_STRING=f"q={search_value}&instrument__title={instrument_title}",
    )
    assert response.status_code == status.HTTP_200_OK

    with pathlib.Path(
        response.context["export_job"].data_file.path,
    ).open() as file:
        content = list(csv.reader(file))
    # Check that we get only csv header and only one expected line
    assert len(content) == 2

    record = content[1]
    assert record[1] == search_value
    assert (
        instrument := Instrument.objects.filter(id=int(record[-1])).first()
    )
    assert instrument.title == instrument_title


@django.test.override_settings(
    IMPORT_EXPORT_SKIP_ADMIN_EXPORT_UI=True,
)
@pytest.mark.usefixtures("existing_artist")
@pytest.mark.django_db(transaction=True)
def test_export_skip_confirmation_page(client: Client, superuser: User):
    """Test export using Django Admin, skipping confirmation page."""
    client.force_login(superuser)

    # Make get request to admin export page
    response = client.get(
        path=reverse("admin:fake_app_artist_export"),
    )
    assert response.status_code == status.HTTP_302_FOUND

    status_response = client.get(response.url)
    assert status_response.status_code == status.HTTP_302_FOUND

    result_response = client.get(status_response.url)
    assert result_response.status_code == status.HTTP_200_OK

    assert ExportJob.objects.exists()
    export_job = ExportJob.objects.first()
    assert export_job.export_status == ExportJob.ExportStatus.EXPORTED, (
        export_job.traceback
    )
