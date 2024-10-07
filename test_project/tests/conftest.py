from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework import test

import pytest

from import_export_extensions.models import ExportJob, ImportJob
from test_project.fake_app.models import Artist, Band, Membership

from ..fake_app import factories
from ..fake_app.factories import ArtistImportJobFactory


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
def uploaded_file(existing_artist: Artist) -> SimpleUploadedFile:
    """Generate valid `Artist` import file."""
    import_job = ArtistImportJobFactory.build(artists=[existing_artist])
    return SimpleUploadedFile(
        "test_file.csv",
        content=import_job.data_file.file.read().encode(),
        content_type="text/plain",
    )


@pytest.fixture
def force_import_artist_job(new_artist: Artist) -> Artist:
    """`ImportJob` with `force_import=True` and file with invalid row."""
    return ArtistImportJobFactory(
        artists=[new_artist],
        is_valid_file=False,
        force_import=True,
    )


@pytest.fixture
def invalid_uploaded_file(new_artist: Artist) -> SimpleUploadedFile:
    """Generate invalid `Artist` imort file."""
    import_job = ArtistImportJobFactory.build(
        artists=[new_artist],
        force_import=True,
        is_valid_file=False,
    )
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
        is_superuser=True,
    )
