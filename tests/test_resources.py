import re

import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError

from example.app import factories, models, resources
from import_export_extensions import results


def test_resource_get_queryset(existing_artist: models.Artist):
    """Check that `get_queryset` contains existing artist."""
    assert existing_artist in resources.SimpleArtistResource().get_queryset()


def test_resource_with_filter_kwargs(existing_artist: models.Artist):
    """Check that `get_queryset` with filter kwargs exclude existing artist."""
    expected_artist_name = "Expected Artist"
    expected_artist = factories.ArtistFactory.create(name=expected_artist_name)
    resource_queryset = resources.SimpleArtistResource(
        filter_kwargs={"name": expected_artist_name},
    ).get_queryset()

    assert existing_artist not in resource_queryset
    assert expected_artist in resource_queryset


def test_resource_with_invalid_filter_kwargs():
    """Check that `get_queryset` raise error if filter kwargs is invalid."""
    with pytest.raises(
        ValidationError,
        match=(
            r"{'id':.*ErrorDetail.*string='Enter a number.', code='invalid'.*"
        ),
    ):
        resources.SimpleArtistResource(
            filter_kwargs={"id": "invalid_id"},
        ).get_queryset()


def test_resource_with_ordering():
    """Check that `get_queryset` with ordering will apply correct ordering."""
    artists = [
        factories.ArtistFactory.create(name=str(num)) for num in range(5)
    ]
    resource_queryset = resources.SimpleArtistResource(
        ordering=("-name",),
    ).get_queryset()
    assert resource_queryset.last() == artists[0]
    assert resource_queryset.first() == artists[-1]


def test_resource_with_invalid_ordering():
    """Check that `get_queryset` raise error if ordering is invalid."""
    with pytest.raises(
        DjangoValidationError,
        match=(
            re.escape(
                "{'ordering': [\"Cannot resolve keyword 'invalid_id' into field.\"]}",  # noqa: E501
            )
        ),
    ):
        resources.SimpleArtistResource(ordering=("invalid_id",)).get_queryset()


def test_resource_get_error_class():
    """Ensure that CeleryResource overrides error class."""
    error_class = resources.SimpleArtistResource().get_error_result_class()
    assert error_class is results.Error
