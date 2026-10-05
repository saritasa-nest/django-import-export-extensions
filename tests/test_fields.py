import pytest
import pytest_lazy_fixtures
import pytest_mock
from django.db import models as django_models

from example.app import factories, models
from import_export_extensions import fields


def test_save_method(
    existing_artist: models.Artist,
    mocker: pytest_mock.MockerFixture,
):
    """Ensure that ``save`` method works properly.

    Logic should be the following:
        method accepts object (Artist) and data about it's bands (
            list of dicts)
        as a result, artist should have info about all his bands

    """
    # set up few artists and bands
    # suggest that our artist was in b1 and b2
    factories.ArtistFactory.create_batch(2)

    b1 = factories.BandFactory.create()
    b2 = factories.BandFactory.create()

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
    factories.MembershipFactory.create()

    field = fields.IntermediateManyToManyField(attribute="bands")
    field.save(existing_artist, {})

    # ensure membership instances created
    assert models.Membership.objects.count() == 3
    assert existing_artist.bands.count() == 2


def test_save_readonly_field(
    existing_artist: models.Artist,
    band: models.Band,
):
    """Simple test to check that readonly field changes nothing."""
    factories.MembershipFactory.create(artist=existing_artist, band=band)
    field = fields.IntermediateManyToManyField(
        attribute="bands",
        readonly=True,
    )
    field.save(existing_artist, {})
    assert existing_artist.bands.all()


def test_save_with_exception_during_full_clean(
    existing_artist: models.Artist,
    band: models.Band,
    mocker: pytest_mock.MockerFixture,
):
    """Check that the exception was handled during full_clean."""
    wrong_format_data = "wrong_date_format"
    column_name = "Bands"

    # suggest widget returned following data
    mocker.patch(
        target=(
            "import_export_extensions.fields.IntermediateManyToManyField.clean"
        ),
        return_value=[
            {
                "object": band,
                "properties": {
                    "date_joined": wrong_format_data,
                },
            },
        ],
    )

    intermediate_field = fields.IntermediateManyToManyField(
        attribute="bands",
        column_name=column_name,
    )
    with pytest.raises(
        ValueError,
        match=(
            f"Column '{column_name}':.*{wrong_format_data}.*value has an "
            "invalid date format. It must be in YYYY-MM-DD format."
        ),
    ):
        intermediate_field.save(existing_artist, {})


def test_get_value(existing_artist: models.Artist):
    """``get_value`` method should return instances of intermediate model."""
    # artist in 2 bands
    factories.MembershipFactory.create(artist=existing_artist)
    factories.MembershipFactory.create(artist=existing_artist)

    # other artist, band and membership
    field = fields.IntermediateManyToManyField(attribute="bands")
    res = field.get_value(existing_artist)

    assert res is not None

    assert res.count() == 2
    assert isinstance(res[0], models.Membership)


def test_get_value_none_attribute(existing_artist: models.Artist):
    """There should be no error if ``attribute`` not set."""
    field = fields.IntermediateManyToManyField()
    assert field.get_value(existing_artist) is None


@pytest.mark.parametrize(
    argnames=["obj", "attribute", "expected_field_params"],
    argvalues=[
        pytest.param(
            pytest_lazy_fixtures.lf("existing_artist"),
            "bands",
            ("artist", "band"),
            id="Object with forward relation",
        ),
        pytest.param(
            pytest_lazy_fixtures.lf("band"),
            "artists",
            ("band", "artist"),
            id="Object with reversed relation",
        ),
    ],
)
def test_get_relation_field_params(
    obj: django_models.Model,
    attribute: str,
    expected_field_params: tuple[str, str],
):
    """Test that method returns correct relation field params."""
    intermediate_field = fields.IntermediateManyToManyField(attribute)
    m2m_rel, field_name, reversed_field_name = (
        intermediate_field.get_relation_field_params(obj)
    )
    assert m2m_rel.through == models.Membership
    assert (field_name, reversed_field_name) == expected_field_params


def test_get_through_model_accessor_name(existing_artist: models.Artist):
    """Test that method returns correct accessor_name."""
    expected_accessor_name = "membership_set"
    attribute = "bands"
    intermediate_field = fields.IntermediateManyToManyField(attribute)
    accessor_name = intermediate_field.get_through_model_accessor_name(
        existing_artist,
        existing_artist._meta.get_field(attribute).remote_field,
    )
    assert accessor_name == expected_accessor_name


def test_get_through_model_accessor_name_with_wrong_relation(
    existing_artist: models.Artist,
    mocker: pytest_mock.MockerFixture,
):
    """Check that method raise error if m2m relation does not exists."""
    attribute = "bands"
    m2m_relation = existing_artist._meta.get_field(attribute).remote_field
    mocker.patch.object(
        target=m2m_relation,
        attribute="through",
        new=models.Instrument,
    )

    intermediate_field = fields.IntermediateManyToManyField(attribute)
    with pytest.raises(
        ValueError,
        match=f"{models.Artist} has no relation with {models.Instrument}",
    ):
        intermediate_field.get_through_model_accessor_name(
            existing_artist,
            m2m_relation,
        )
