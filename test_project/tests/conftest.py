from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework import test

import pytest

from import_export_extensions.models import ExportJob, ImportJob

from ..fake_app import factories
from ..fake_app.factories import ArtistImportJobFactory
from ..fake_app.models import Artist, Band, Membership


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
def artist_import_job(
    superuser: User,
    existing_artist: Artist,
) -> ImportJob:
    """Return `ImportJob` instance with specified artist."""
    return factories.ArtistImportJobFactory.create(
        created_by=superuser,
        artists=[existing_artist],
    )


@pytest.fixture
def artist_export_job(
    superuser: User,
) -> ExportJob:
    """Return `ExportJob` instance."""
    return factories.ArtistExportJobFactory.create(created_by=superuser)


@pytest.fixture
def band() -> Band:
    """Return `Band` instance."""
    return factories.BandFactory.create(title="Aerosmith")


@pytest.fixture
def membership(band: Band) -> Membership:
    """Return `Membership` instance with specified band."""
    return factories.MembershipFactory.create(band=band)


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
def force_import_artist_job(
    superuser: User,
    new_artist: Artist,
) -> ImportJob:
    """`ImportJob` with `force_import=True` and file with invalid row."""
    return ArtistImportJobFactory.create(
        artists=[new_artist],
        is_valid_file=False,
        force_import=True,
        created_by=superuser,
    )


@pytest.fixture
def user():
    """Return user instance."""
    return get_user_model().objects.create(
        username="test_login",
        email="test@localhost.com",
        password="test_pass",
        is_staff=False,
        is_superuser=False,
    )


@pytest.fixture
def superuser():
    """Return superuser instance."""
    return get_user_model().objects.create(
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
