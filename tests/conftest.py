import typing

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import test

from example.app import factories, models
from import_export_extensions import models as ie_models


def pytest_configure() -> None:
    """Set up Django settings for tests.

    `pytest` automatically calls this function once when tests are run.

    """
    settings.TESTING = True
    # Disable async task execution while tests running
    settings.CELERY_TASK_ALWAYS_EAGER = True


@pytest.fixture(scope="session", autouse=True)
def django_db_setup(django_db_setup: typing.Any) -> None:
    """Set up test db for testing."""


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(
    django_db_setup: typing.Any,
    db: None,
) -> None:
    """Allow all tests to access DB."""


@pytest.fixture(scope="session", autouse=True)
def _temp_directory_for_media(tmpdir_factory: pytest.TempdirFactory) -> None:
    """Fixture that set temp directory for all media files.

    This fixture changes DEFAULT_FILE_STORAGE or STORAGES variable
    to filesystem and provides temp dir for media.
    PyTest cleans up this temp dir by itself after few test runs

    """
    if hasattr(settings, "STORAGES"):
        settings.STORAGES["default"]["BACKEND"] = (
            "django.core.files.storage.FileSystemStorage"
        )
    else:
        settings.DEFAULT_FILE_STORAGE = (
            "django.core.files.storage.FileSystemStorage"
        )
    media = tmpdir_factory.mktemp("tmp_media")
    settings.MEDIA_ROOT = media


@pytest.fixture
def existing_artist() -> models.Artist:
    """Return existing in db `Artist` instance."""
    return factories.ArtistFactory.create()


@pytest.fixture
def new_artist() -> models.Artist:
    """Return not existing `Artist` instance."""
    return factories.ArtistFactory.build(
        instrument=factories.InstrumentFactory.create(),
    )


@pytest.fixture
def artist_import_job(
    superuser: User,
    existing_artist: models.Artist,
) -> ie_models.ImportJob:
    """Return `ImportJob` instance with specified artist."""
    return factories.ArtistImportJobFactory.create(
        created_by=superuser,
        artists=[existing_artist],
    )


@pytest.fixture
def artist_export_job(
    superuser: User,
) -> ie_models.ExportJob:
    """Return `ExportJob` instance."""
    return factories.ArtistExportJobFactory.create(created_by=superuser)


@pytest.fixture
def band() -> models.Band:
    """Return `Band` instance."""
    return factories.BandFactory.create(title="Aerosmith")


@pytest.fixture
def membership(band: models.Band) -> models.Membership:
    """Return `Membership` instance with specified band."""
    return factories.MembershipFactory.create(band=band)


@pytest.fixture
def uploaded_file(existing_artist: models.Artist) -> SimpleUploadedFile:
    """Generate valid `Artist` import file."""
    import_job = factories.ArtistImportJobFactory.build(
        artists=[existing_artist],
    )
    return SimpleUploadedFile(
        "test_file.csv",
        content=import_job.data_file.file.read().encode(),
        content_type="text/plain",
    )


@pytest.fixture
def force_import_artist_job(
    superuser: User,
    new_artist: models.Artist,
) -> ie_models.ImportJob:
    """`ImportJob` with `force_import=True` and file with invalid row."""
    return factories.ArtistImportJobFactory.create(
        artists=[new_artist],
        is_valid_file=False,
        force_import=True,
        created_by=superuser,
    )


@pytest.fixture
def user() -> User:
    """Return user instance."""
    return User.objects.create(
        username="test_login",
        email="test@localhost.com",
        password="test_pass",
        is_staff=False,
        is_superuser=False,
    )


@pytest.fixture
def superuser() -> User:
    """Return superuser instance."""
    return User.objects.create(
        username="admin_login",
        email="admin@localhost.com",
        password="admin_pass",
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def api_client() -> test.APIClient:
    """Create api client."""
    return test.APIClient()


@pytest.fixture
def admin_api_client(
    superuser: User,
    api_client: test.APIClient,
) -> test.APIClient:
    """Authenticate admin_user and return api client."""
    api_client.force_authenticate(user=superuser)
    return api_client
