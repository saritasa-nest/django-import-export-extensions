import django.test
import pytest
import pytest_mock
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.test.client import Client
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from import_export_extensions.models import ExportJob, ImportJob


@django.test.override_settings(
    IMPORT_EXPORT_RERUN_ENABLED=True,
)
@pytest.mark.django_db
def test_export_job_rerun_updates_fields(
    client: Client,
    superuser: User,
    artist_export_job: ExportJob,
    mocker: pytest_mock.MockerFixture,
):
    """Test export job rerun updates/clears job fields."""
    client.force_login(superuser)

    # Prepare job with some "old" data
    old_task_id = "old-task-id"
    old_date = timezone.now() - timezone.timedelta(days=1)
    artist_export_job.export_status = ExportJob.ExportStatus.EXPORTED
    artist_export_job.export_task_id = old_task_id
    artist_export_job.export_started = old_date
    artist_export_job.export_finished = old_date
    artist_export_job.error_message = "Old error"
    artist_export_job.traceback = "Old traceback"
    artist_export_job.data_file.save(
        "old_file.csv",
        ContentFile(b"old data"),
        save=False,
    )
    artist_export_job.save()

    # Mock rerun to avoid actual celery task trigger
    # Admin call: obj.rerun() -> calls _start_export_data_task via on_commit
    mocker.patch(
        "import_export_extensions.models.export_job.ExportJob._start_export_data_task",
    )

    response = client.get(
        path=reverse(
            "admin:import_export_extensions_exportjob_rerun",
            kwargs={"job_id": artist_export_job.pk},
        ),
    )

    assert response.status_code == status.HTTP_302_FOUND
    artist_export_job.refresh_from_db()
    assert artist_export_job.export_status == ExportJob.ExportStatus.CREATED
    assert artist_export_job.export_task_id != old_task_id
    assert artist_export_job.export_task_id != ""
    assert artist_export_job.export_started is None
    assert artist_export_job.export_finished is None
    assert artist_export_job.error_message == ""
    assert artist_export_job.traceback == ""
    assert not artist_export_job.data_file
    assert artist_export_job.modified > old_date


@django.test.override_settings(
    IMPORT_EXPORT_RERUN_ENABLED=True,
)
@pytest.mark.django_db
def test_import_job_rerun_updates_fields(
    client: Client,
    superuser: User,
    artist_import_job: ImportJob,
    mocker: pytest_mock.MockerFixture,
):
    """Test import job rerun updates/clears job fields."""
    client.force_login(superuser)

    # Prepare job with some "old" data
    old_task_id = "old-task-id"
    old_date = timezone.now() - timezone.timedelta(days=1)

    artist_import_job.import_status = ImportJob.ImportStatus.IMPORTED
    artist_import_job.parse_task_id = old_task_id
    artist_import_job.import_task_id = old_task_id
    artist_import_job.parse_finished = old_date
    artist_import_job.import_started = old_date
    artist_import_job.import_finished = old_date
    artist_import_job.error_message = "Old error"
    artist_import_job.traceback = "Old traceback"
    artist_import_job.input_errors_file.save(
        "errors.csv",
        ContentFile(b"old errors"),
        save=False,
    )
    artist_import_job.save()

    # Mock rerun to avoid actual celery task trigger
    mocker.patch(
        "import_export_extensions.models.import_job.ImportJob.start_parse_data_task",
    )

    response = client.get(
        path=reverse(
            "admin:import_export_extensions_importjob_rerun",
            kwargs={"job_id": artist_import_job.pk},
        ),
    )

    assert response.status_code == status.HTTP_302_FOUND
    artist_import_job.refresh_from_db()
    assert artist_import_job.import_status == ImportJob.ImportStatus.CREATED
    assert artist_import_job.parse_task_id != old_task_id
    assert artist_import_job.parse_task_id != ""
    assert artist_import_job.import_task_id == ""
    assert artist_import_job.parse_finished is None
    assert artist_import_job.import_started is None
    assert artist_import_job.import_finished is None
    assert artist_import_job.error_message == ""
    assert artist_import_job.traceback == ""
    assert not artist_import_job.input_errors_file
    assert artist_import_job.modified > old_date


@django.test.override_settings(
    IMPORT_EXPORT_RERUN_ENABLED=True,
)
@pytest.mark.django_db
def test_import_job_rerun_updates_fields_skip_parse(
    client: Client,
    superuser: User,
    artist_import_job: ImportJob,
    mocker: pytest_mock.MockerFixture,
):
    """Test import job rerun updates fields when skip_parse_step is True."""
    client.force_login(superuser)

    # Prepare job with some "old" data and skip_parse_step=True
    old_task_id = "old-task-id"
    old_date = timezone.now() - timezone.timedelta(days=1)
    artist_import_job.import_status = ImportJob.ImportStatus.IMPORTED
    artist_import_job.import_task_id = old_task_id
    artist_import_job.import_started = old_date
    artist_import_job.import_finished = old_date
    artist_import_job.error_message = "Old error"
    artist_import_job.traceback = "Old traceback"
    artist_import_job.skip_parse_step = True
    artist_import_job.save()

    # Mock rerun to avoid actual celery task trigger
    mocker.patch(
        "import_export_extensions.models.import_job.ImportJob._start_import_data_task",
    )

    response = client.get(
        path=reverse(
            "admin:import_export_extensions_importjob_rerun",
            kwargs={"job_id": artist_import_job.pk},
        ),
    )

    assert response.status_code == status.HTTP_302_FOUND
    artist_import_job.refresh_from_db()
    assert artist_import_job.import_status == ImportJob.ImportStatus.CREATED
    assert artist_import_job.import_task_id != old_task_id
    assert artist_import_job.import_task_id != ""
    assert artist_import_job.parse_task_id == ""
    assert artist_import_job.import_started > old_date
    assert artist_import_job.import_finished is None
    assert artist_import_job.error_message == ""
    assert artist_import_job.traceback == ""
    assert artist_import_job.modified > old_date


@django.test.override_settings(
    IMPORT_EXPORT_RERUN_ENABLED=True,
)
@pytest.mark.django_db
def test_export_job_rerun_endpoint_enabled(
    client: Client,
    superuser: User,
    artist_export_job: ExportJob,
    mocker: pytest_mock.MockerFixture,
):
    """Test export job rerun endpoint is available when enabled."""
    client.force_login(superuser)

    # Mock rerun to avoid actual job execution
    mocker.patch("import_export_extensions.models.ExportJob.rerun")

    response = client.get(
        path=reverse(
            "admin:import_export_extensions_exportjob_rerun",
            kwargs={"job_id": artist_export_job.pk},
        ),
    )

    assert response.status_code == status.HTTP_302_FOUND
    # BaseImportExportJobAdminMixin.rerun redirects
    # to change view for ExportJob
    expected_url = reverse(
        "admin:import_export_extensions_exportjob_change",
        kwargs={"object_id": artist_export_job.pk},
    )
    assert response.url == expected_url


@django.test.override_settings(
    IMPORT_EXPORT_RERUN_ENABLED=True,
)
@pytest.mark.django_db
def test_import_job_rerun_endpoint_enabled(
    client: Client,
    superuser: User,
    artist_import_job: ImportJob,
    mocker: pytest_mock.MockerFixture,
):
    """Test import job rerun endpoint is available when enabled."""
    client.force_login(superuser)

    # Mock rerun to avoid actual job execution
    mocker.patch("import_export_extensions.models.ImportJob.rerun")

    response = client.get(
        path=reverse(
            "admin:import_export_extensions_importjob_rerun",
            kwargs={"job_id": artist_import_job.pk},
        ),
    )

    assert response.status_code == status.HTTP_302_FOUND
    # BaseImportExportJobAdminMixin.rerun redirects
    # to results page for ImportJob
    expected_url = reverse(
        "admin:fake_app_artist_import_job_results",
        kwargs={"job_id": artist_import_job.pk},
    )
    assert response.url == expected_url
