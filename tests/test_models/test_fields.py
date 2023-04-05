from pytest_mock import MockerFixture

from import_export_extensions.fields import IntermediateManyToManyField

from ..fake_app import factories
from ..fake_app.models import Artist, Membership


def test_save_method(existing_artist: Artist, mocker: MockerFixture):
    """Ensure that ``save`` method works properly.

    Logic should be the following:
        method accepts object (Artist) and data about it's bands (
            list of dicts)
        as a result, artist should have info about all his bands

    """
    # set up few artists and bands
    # suggest that our artist was in b1 and b2
    factories.ArtistFactory.create_batch(2)

    b1 = factories.BandFactory()
    b2 = factories.BandFactory()

    # suggest widget returned following data
    band_data = [
        {"object": b1, "properties": {"date_joined": "1992-11-11"}},
        {"object": b2, "properties": {"date_joined": "2016-11-11"}},
    ]
    mocker.patch(
        target=(
            "import_export_extensions.fields.IntermediateManyToManyField.clean"
        ),
        return_value=band_data,
    )

    # and there is another artist in other band
    factories.MembershipFactory()

    field = IntermediateManyToManyField(attribute="bands")
    field.save(existing_artist, {})

    # ensure membership instances created
    assert Membership.objects.count() == 3
    assert existing_artist.bands.count() == 2


def test_save_readonly_field(existing_artist: Artist):
    """Simple test to check that readonly field changes nothing."""
    field = IntermediateManyToManyField(attribute="bands", readonly=True)
    field.save(existing_artist, {})


def test_get_value(existing_artist: Artist):
    """``get_value`` method should return instances of intermediate model."""
    # artist in 2 bands
    factories.MembershipFactory(artist=existing_artist)
    factories.MembershipFactory(artist=existing_artist)

    # other artist, band and membership
    field = IntermediateManyToManyField(attribute="bands")
    res = field.get_value(existing_artist)

    assert res is not None

    assert res.count() == 2
    assert isinstance(res[0], Membership)


def test_get_value_none_attribute(existing_artist: Artist):
    """There should be no error if ``attribute`` not set."""
    field = IntermediateManyToManyField()
    assert field.get_value(existing_artist) is None
