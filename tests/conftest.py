from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

import pytest

from tests.fake_app.models import Artist, Band, Membership

from import_export_extensions.models import ExportJob, ImportJob

from .fake_app import factories
from .fake_app.factories import ArtistImportJobFactory


@pytest.fixture(scope="session", autouse=True)
def django_db_setup(django_db_setup):
    """Set up test db for testing."""


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(django_db_setup, db):
    """Allow all tests to access DB."""


@pytest.fixture
def existing_artist():
    """Return existing in db `Artist` instance."""
    return factories.ArtistFactory()


@pytest.fixture
def new_artist():
    """Return not existing `Artist` instance."""
    return factories.ArtistFactory.build(
        instrument=factories.InstrumentFactory(),
    )


@pytest.fixture
def artist_import_job(existing_artist: Artist) -> ImportJob:
    """Return `ImportJob` instance with specified artist."""
    return factories.ArtistImportJobFactory(artists=[existing_artist])


@pytest.fixture
def artist_export_job() -> ExportJob:
    """Return `ExportJob` instance."""
    return factories.ArtistExportJobFactory()


@pytest.fixture
def band() -> Band:
    """Return `Band` instance."""
    return factories.BandFactory(title="Aerosmith")


@pytest.fixture
def membership(band: Band) -> Membership:
    """Return `Membership` instance with specified band."""
    return factories.MembershipFactory(band=band)


@pytest.fixture
def uploaded_file(existing_artist: Artist):
    """Generate valid `Artist` import file."""
    import_job = ArtistImportJobFactory.build(artists=[existing_artist])
    return SimpleUploadedFile(
        "test_file.csv",
        content=import_job.data_file.file.read().encode(),
        content_type="text/plain",
    )


@pytest.fixture
def superuser():
    """Return superuser instance."""
    return get_user_model().objects.create(
        username="test_login",
        email="test@localhost.com",
        password="test_pass",
        is_staff=True,
    )


@pytest.fixture(scope="session", autouse=True)
def temp_directory_for_media(tmpdir_factory):
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
