from rest_framework.exceptions import ValidationError

import pytest

from import_export_extensions import results
from test_project.fake_app.factories import ArtistFactory
from test_project.fake_app.models import Artist

from ..fake_app.resources import SimpleArtistResource


def test_resource_get_queryset(existing_artist: Artist):
    """Check that `get_queryset` contains existing artist."""
    assert existing_artist in SimpleArtistResource().get_queryset()


def test_resource_with_filter_kwargs(existing_artist: Artist):
    """Check that `get_queryset` with filter kwargs exclude existing artist."""
    expected_artist_name = "Expected Artist"
    expected_artist = ArtistFactory(name=expected_artist_name)
    resource_queryset = SimpleArtistResource(
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
        SimpleArtistResource(
            filter_kwargs={"id": "invalid_id"},
        ).get_queryset()


def test_resource_get_error_class():
    """Ensure that CeleryResource overrides error class."""
    error_class = SimpleArtistResource().get_error_result_class()
    assert error_class is results.Error
