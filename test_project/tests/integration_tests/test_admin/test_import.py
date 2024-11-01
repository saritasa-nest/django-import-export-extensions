"""There are kind a functional tests for import using Django Admin."""

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.client import Client
from django.urls import reverse

from rest_framework import status

import pytest
import pytest_mock
from celery import states
from pytest_lazy_fixtures import lf

from import_export_extensions.models import ImportJob
from test_project.fake_app.factories import ArtistImportJobFactory


@pytest.mark.usefixtures("existing_artist")
@pytest.mark.django_db(transaction=True)
def test_import_using_admin_model(
    client: Client,
    superuser: User,
    uploaded_file: SimpleUploadedFile,
):
    """Test entire importing process using Django Admin.

    There is following workflow:
        1. Go to Artist Import page
        2. Start Import Job with chosen file
        3. Redirect to the import job parsing result page through
           the status page
        4. Confirm import
        5. Redirect to the import job importing page through the status page

    """
    client.force_login(superuser)

    # Go to import page in admin panel
    import_response = client.get(
        path=reverse("admin:fake_app_artist_import"),
    )
    assert import_response.status_code == status.HTTP_200_OK

    # Start import job using admin panel
    start_import_job_response = client.post(
        path=reverse("admin:fake_app_artist_import"),
        data={
            "import_file": uploaded_file,
            "format": 0,  # Choose CSV format
        },
    )
    assert start_import_job_response.status_code == status.HTTP_302_FOUND

    # Go to import job status page
    # Ensure there is another one redirect because import job finished
    status_page_response = client.get(path=start_import_job_response.url)
    assert status_page_response.status_code == status.HTTP_302_FOUND

    assert ImportJob.objects.exists()

    import_job = ImportJob.objects.first()

    # Go to results page
    result_page_get_response = client.get(status_page_response.url)
    assert result_page_get_response.status_code == status.HTTP_200_OK

    # Confirm import on result page
    confirm_response = client.post(
        path=status_page_response.url,
        data={"confirm": "Confirm import"},
    )
    assert confirm_response.status_code == status.HTTP_302_FOUND

    # Ensure import job finished and redirected to result page
    import_status_response = client.get(path=confirm_response.url)
    assert import_status_response.status_code == status.HTTP_302_FOUND

    result_response = client.get(path=import_status_response.url)

    assert result_response.status_code == status.HTTP_200_OK

    import_job.refresh_from_db()
    assert import_job.import_status == ImportJob.ImportStatus.IMPORTED


@pytest.mark.parametrize(
    argnames=["view_name", "path_kwargs"],
    argvalues=[
        pytest.param(
            "admin:fake_app_artist_import",
            None,
            id="Test access to `celery_import_action`",
        ),
        pytest.param(
            "admin:fake_app_artist_import_job_status",
            {"job_id": lf("artist_import_job.pk")},
            id="Test access to `import_job_status_view`",
        ),
        pytest.param(
            "admin:fake_app_artist_import_job_results",
            {"job_id": lf("artist_import_job.pk")},
            id="Test access to `import_job_results_view`",
        ),
    ],
)
def test_import_using_admin_model_without_permissions(
    client: Client,
    superuser: User,
    view_name: str,
    path_kwargs: dict[str, str],
    mocker: pytest_mock.MockerFixture,
):
    """Test access to celery-import endpoints forbidden without permission."""
    client.force_login(superuser)
    mocker.patch(
        "test_project.fake_app.admin.ArtistAdmin.has_import_permission",
        return_value=False,
    )
    response = client.get(
        path=reverse(
            view_name,
            kwargs=path_kwargs,
        ),
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_celery_import_status_view_during_import(
    client: Client,
    superuser: User,
    mocker: pytest_mock.MockerFixture,
):
    """Test import status page when import in progress."""
    client.force_login(superuser)

    mocker.patch("import_export_extensions.tasks.parse_data_task.apply_async")
    artist_import_job = ArtistImportJobFactory(skip_parse_step=True)
    artist_import_job.import_status = ImportJob.ImportStatus.IMPORTING
    artist_import_job.save()

    response = client.get(
        path=reverse(
            "admin:fake_app_artist_import_job_status",
            kwargs={"job_id": artist_import_job.pk},
        ),
    )

    expected_import_job_url = reverse(
        "admin:import_job_progress",
        kwargs={"job_id": artist_import_job.id},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.context["import_job_url"] == expected_import_job_url


@pytest.mark.parametrize(
    argnames="incorrect_job_status",
    argvalues=[
        ImportJob.ImportStatus.CREATED,
        ImportJob.ImportStatus.PARSING,
        ImportJob.ImportStatus.PARSE_ERROR,
        ImportJob.ImportStatus.CONFIRMED,
        ImportJob.ImportStatus.IMPORTING,
        ImportJob.ImportStatus.CANCELLED,
    ],
)
def test_celery_import_results_view_redirect_to_status_page(
    client: Client,
    superuser: User,
    incorrect_job_status: ImportJob.ImportStatus,
    mocker: pytest_mock.MockerFixture,
):
    """Test redirect to import status page when job in not result status."""
    client.force_login(superuser)

    mocker.patch("import_export_extensions.tasks.parse_data_task.apply_async")
    artist_import_job = ArtistImportJobFactory()
    artist_import_job.import_status = incorrect_job_status
    artist_import_job.save()

    response = client.get(
        path=reverse(
            "admin:fake_app_artist_import_job_results",
            kwargs={"job_id": artist_import_job.pk},
        ),
    )

    expected_redirect_url = reverse(
        "admin:fake_app_artist_import_job_status",
        kwargs={"job_id": artist_import_job.pk},
    )
    assert response.status_code == status.HTTP_302_FOUND
    assert response.url == expected_redirect_url


@pytest.mark.parametrize(
    argnames="incorrect_job_status",
    argvalues=[
        ImportJob.ImportStatus.INPUT_ERROR,
        ImportJob.ImportStatus.IMPORT_ERROR,
        ImportJob.ImportStatus.IMPORTED,
    ],
)
def test_celery_import_results_confirm_forbidden(
    client: Client,
    superuser: User,
    incorrect_job_status: ImportJob.ImportStatus,
    mocker: pytest_mock.MockerFixture,
):
    """Check that confirm from result page forbidden for not PARSED jobs."""
    client.force_login(superuser)

    mocker.patch("import_export_extensions.tasks.parse_data_task.apply_async")
    artist_import_job = ArtistImportJobFactory()
    artist_import_job.import_status = incorrect_job_status
    artist_import_job.save()

    response = client.post(
        path=reverse(
            "admin:fake_app_artist_import_job_results",
            kwargs={"job_id": artist_import_job.pk},
        ),
        data={"confirm": "Confirm import"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.usefixtures("existing_artist")
def test_import_admin_has_same_formats(
    client: Client,
    superuser: User,
    artist_import_job: ImportJob,
):
    """Ensure input formats on import forms are the same.

    Ensure Import forms on import and on import result pages
    fetch format choices from the same source.

    """
    client.force_login(superuser)
    artist_import_job.import_status = ImportJob.ImportStatus.IMPORTED
    artist_import_job.save()
    import_response = client.get(
        path=reverse("admin:fake_app_artist_import"),
    )
    import_response_result = client.get(
        path=reverse(
            "admin:fake_app_artist_import_job_results",
            kwargs={"job_id": artist_import_job.id},
        ),
    )
    import_response_form = import_response.context_data["form"]
    import_response_result_form = import_response_result.context_data[
        "import_form"
    ]
    assert (
        import_response_form.fields["format"].choices
        == import_response_result_form.fields["format"].choices
    )


@pytest.mark.django_db(transaction=True)
def test_import_progress_during_import(
    client: Client,
    superuser: User,
    mocker: pytest_mock.MockerFixture,
):
    """Test import job admin progress page during import."""
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

    artist_import_job = ArtistImportJobFactory(
        skip_parse_step=True,
    )
    artist_import_job.import_status = ImportJob.ImportStatus.IMPORTING
    artist_import_job.save()

    response = client.post(
        path=reverse(
            "admin:import_job_progress",
            kwargs={"job_id": artist_import_job.pk},
        ),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status": ImportJob.ImportStatus.IMPORTING.title(),
        "state": "SUCCESS",
        "percent": expected_percent,
        **fake_progress_info,
    }


@pytest.mark.django_db(transaction=True)
def test_import_progress_after_complete_import(
    client: Client,
    superuser: User,
):
    """Test import job admin progress page after complete import."""
    client.force_login(superuser)

    artist_import_job = ArtistImportJobFactory(
        skip_parse_step=True,
    )
    artist_import_job.refresh_from_db()

    response = client.post(
        path=reverse(
            "admin:import_job_progress",
            kwargs={"job_id": artist_import_job.pk},
        ),
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status": artist_import_job.import_status.title(),
    }


@pytest.mark.django_db(transaction=True)
def test_import_progress_with_deleted_import_job(
    client: Client,
    superuser: User,
    mocker: pytest_mock.MockerFixture,
):
    """Test import job admin progress page with deleted import job."""
    client.force_login(superuser)

    mocker.patch("import_export_extensions.tasks.import_data_task.apply_async")
    artist_import_job = ArtistImportJobFactory()
    job_id = artist_import_job.id
    artist_import_job.delete()

    expected_error_message = "ImportJob matching query does not exist."

    response = client.post(
        path=reverse(
            "admin:import_job_progress",
            kwargs={
                "job_id": job_id,
            },
        ),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["validation_error"] == expected_error_message


@pytest.mark.django_db(transaction=True)
def test_import_progress_with_failed_celery_task(
    client: Client,
    superuser: User,
    mocker: pytest_mock.MockerFixture,
):
    """Test than after celery fail ImportJob will be in import error status."""
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
    artist_import_job = ArtistImportJobFactory()
    artist_import_job.refresh_from_db()
    artist_import_job.confirm_import()
    artist_import_job.import_status = ImportJob.ImportStatus.IMPORTING
    artist_import_job.save()

    response = client.post(
        path=reverse(
            "admin:import_job_progress",
            kwargs={
                "job_id": artist_import_job.id,
            },
        ),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["state"] == states.FAILURE
    artist_import_job.refresh_from_db()
    assert (
        artist_import_job.import_status == ImportJob.ImportStatus.IMPORT_ERROR
    )


@pytest.mark.django_db(transaction=True)
def test_cancel_import_admin_action(
    client: Client,
    superuser: User,
    mocker: pytest_mock.MockerFixture,
):
    """Test `cancel_import` via admin action."""
    client.force_login(superuser)

    revoke_mock = mocker.patch("celery.current_app.control.revoke")
    import_data_mock = mocker.patch(
        "import_export_extensions.models.ImportJob.import_data",
    )
    artist_import_job = ArtistImportJobFactory()
    artist_import_job.refresh_from_db()
    artist_import_job.confirm_import()

    response = client.post(
        reverse("admin:import_export_extensions_importjob_changelist"),
        data={
            "action": "cancel_jobs",
            "_selected_action": [artist_import_job.pk],
        },
        follow=True,
    )
    artist_import_job.refresh_from_db()

    assert response.status_code == status.HTTP_200_OK
    assert artist_import_job.import_status == ImportJob.ImportStatus.CANCELLED
    assert (
        response.context["messages"]._loaded_data[0].message
        == f"Import of {artist_import_job} canceled"
    )
    import_data_mock.assert_called_once()
    revoke_mock.assert_called_once_with(
        artist_import_job.import_task_id,
        terminate=True,
    )


@pytest.mark.django_db(transaction=True)
def test_cancel_import_admin_action_with_incorrect_import_job_status(
    client: Client,
    superuser: User,
    mocker: pytest_mock.MockerFixture,
):
    """Test `cancel_import` via admin action with wrong import job status."""
    client.force_login(superuser)

    revoke_mock = mocker.patch("celery.current_app.control.revoke")
    artist_import_job = ArtistImportJobFactory()

    expected_error_message = (
        f"ImportJob with id {artist_import_job.pk} has incorrect status"
    )

    response = client.post(
        reverse("admin:import_export_extensions_importjob_changelist"),
        data={
            "action": "cancel_jobs",
            "_selected_action": [artist_import_job.pk],
        },
        follow=True,
    )
    artist_import_job.refresh_from_db()

    assert response.status_code == status.HTTP_200_OK
    assert artist_import_job.import_status == ImportJob.ImportStatus.PARSED
    assert (
        expected_error_message
        in response.context["messages"]._loaded_data[0].message
    )
    revoke_mock.assert_not_called()


@pytest.mark.django_db(transaction=True)
def test_confirm_import_admin_action(
    client: Client,
    superuser: User,
    mocker: pytest_mock.MockerFixture,
):
    """Test `confirm_import` via admin action."""
    client.force_login(superuser)

    import_data_mock = mocker.patch(
        "import_export_extensions.models.ImportJob.import_data",
    )
    artist_import_job = ArtistImportJobFactory()
    artist_import_job.refresh_from_db()

    response = client.post(
        reverse("admin:import_export_extensions_importjob_changelist"),
        data={
            "action": "confirm_jobs",
            "_selected_action": [artist_import_job.pk],
        },
        follow=True,
    )
    artist_import_job.refresh_from_db()

    assert response.status_code == status.HTTP_200_OK
    assert artist_import_job.import_status == ImportJob.ImportStatus.CONFIRMED
    assert (
        response.context["messages"]._loaded_data[0].message
        == f"Import of {artist_import_job} confirmed"
    )
    import_data_mock.assert_called_once()


@pytest.mark.django_db(transaction=True)
def test_confirm_import_admin_action_with_incorrect_import_job_status(
    client: Client,
    superuser: User,
):
    """Test `confirm_import` via admin action with wrong import job status."""
    client.force_login(superuser)

    artist_import_job = ArtistImportJobFactory()
    artist_import_job.import_status = ImportJob.ImportStatus.CANCELLED
    artist_import_job.save()

    expected_error_message = (
        f"ImportJob with id {artist_import_job.pk} has incorrect status"
    )

    response = client.post(
        reverse("admin:import_export_extensions_importjob_changelist"),
        data={
            "action": "confirm_jobs",
            "_selected_action": [artist_import_job.pk],
        },
        follow=True,
    )
    artist_import_job.refresh_from_db()

    assert response.status_code == status.HTTP_200_OK
    assert artist_import_job.import_status == ImportJob.ImportStatus.CANCELLED
    assert (
        expected_error_message
        in response.context["messages"]._loaded_data[0].message
    )


@pytest.mark.parametrize(
    argnames=["job_status", "expected_fieldsets"],
    argvalues=[
        pytest.param(
            ImportJob.ImportStatus.CREATED,
            tuple(),
            id="Get fieldsets for job in status CREATED",
        ),
        pytest.param(
            ImportJob.ImportStatus.IMPORTED,
            (
                ("_show_results",),
                (
                    "input_errors_file",
                    "_input_errors",
                ),
            ),
            id="Get fieldsets for job in status IMPORTED",
        ),
        pytest.param(
            ImportJob.ImportStatus.IMPORTING,
            (
                (
                    "import_status",
                    "import_progressbar",
                ),
            ),
            id="Get fieldsets for job in status IMPORTING",
        ),
        pytest.param(
            ImportJob.ImportStatus.IMPORT_ERROR,
            (("traceback",),),
            id="Get fieldsets for job in status IMPORT_ERROR",
        ),
    ],
)
def test_get_fieldsets_by_import_job_status(
    client: Client,
    superuser: User,
    job_status: ImportJob.ImportStatus,
    expected_fieldsets: tuple[tuple[str]],
    mocker: pytest_mock.MockerFixture,
):
    """Test that appropriate fieldsets returned for different job statuses."""
    client.force_login(superuser)

    mocker.patch(
        "import_export_extensions.models.ImportJob.import_data",
    )
    artist_import_job = ArtistImportJobFactory()
    artist_import_job.import_status = job_status
    artist_import_job.save()

    response = client.get(
        reverse(
            "admin:import_export_extensions_importjob_change",
            kwargs={"object_id": artist_import_job.pk},
        ),
    )

    fieldsets = response.context["adminform"].fieldsets
    fields = [fields["fields"] for _, fields in fieldsets]

    assert tuple(fields) == (
        (
            "import_status",
            "_model",
            "created_by",
            "created",
            "parse_finished",
            "import_started",
            "import_finished",
        ),
        *expected_fieldsets,
        (
            "data_file",
            "resource_path",
            "resource_kwargs",
        ),
    )
