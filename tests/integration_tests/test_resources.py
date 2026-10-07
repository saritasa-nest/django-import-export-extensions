import pytest

from example.app import factories, models, resources
from import_export_extensions import resources as ie_resources


@pytest.fixture
def three_bands_artist(existing_artist: models.Artist) -> models.Artist:
    """Return artist with three memberships."""
    factories.MembershipFactory.create_batch(3, artist=existing_artist)
    return existing_artist


@pytest.fixture
def artist_resource_with_m2m() -> resources.ArtistResourceWithM2M:
    """Return Artist resource with Many2Many field instance."""
    return resources.ArtistResourceWithM2M()


def _import_export_artist(
    resource: ie_resources.CeleryModelResource,
    artist: models.Artist,
) -> models.Artist:
    """Return restored Artist."""
    dataset = resource.export(
        queryset=models.Artist.objects.filter(id=artist.pk),
    )

    # delete info about this artist
    artist.delete()

    # get new instance of resource
    resource = resource.__class__()

    # restore info from dataset
    result = resource.import_data(dataset)
    return models.Artist.objects.get(id=result.rows[0].object_id)


def test_correct_restoring(
    artist_resource_with_m2m: ie_resources.CeleryModelResource,
    three_bands_artist: models.Artist,
):
    """Test that restoring works correct.

    Take a look at ``app.models``. So we want to export
    ``Artist`` with info about his bands. And we want to store info about
    when artist joined some band in the same flat dataset.

    Test case is following:
        create artist's bio (with joined bands)
        create few other artists
        remove info about original artist
        restore his info from exported dataset

    """
    # retrieve artist from DB
    restored_artist = _import_export_artist(
        resource=artist_resource_with_m2m,
        artist=three_bands_artist,
    )
    restored_membership = models.Membership.objects.filter(
        artist=restored_artist,
    )

    # check that restored artist contain same info
    assert restored_artist.name == three_bands_artist.name

    memberships = list(models.Membership.objects.all())
    # check info about his bands
    expected_bands = {membership.band.id for membership in memberships}
    restored_bands = set(restored_artist.bands.values_list("id", flat=True))

    assert expected_bands == restored_bands

    expected_join_dates = {
        membership.date_joined for membership in memberships
    }
    restored_join_dates = set(
        restored_membership.values_list("date_joined", flat=True),
    )

    assert expected_join_dates == restored_join_dates
