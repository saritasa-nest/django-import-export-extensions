import typing

import pytest
from import_export.formats import base_formats as formats

from tests.fake_app.models import Artist
from tests.fake_app.resources import ArtistResourceWithM2M

from import_export_extensions import forms, resources


@pytest.fixture
def available_formats():
    """Return a subset of formats."""
    return [
        formats.CSV,
        formats.XLS,
        formats.XLSX,
        formats.JSON,
    ]


@pytest.fixture
def limited_formats_artist_resource():
    """Return a resource with limited supported formats."""
    class LimitedFormatArtistResource(resources.CeleryModelResource):
        """Artist resource with limited supported formats."""
        SUPPORTED_FORMATS = [formats.CSV, formats.JSON]

        class Meta:
            model = Artist

    return LimitedFormatArtistResource


def test_export_form_set_xlsx_as_initial_choice(
    available_formats: list[typing.Type[formats.Format]],
):
    """Ensure xlsx is initial choice for export form."""
    export_form = forms.ExportForm(formats=available_formats)
    initial_choice = export_form.fields["file_format"].initial
    xlsx_choice_index = available_formats.index(formats.XLSX)

    assert initial_choice == xlsx_choice_index


def test_form_init_blank_format_and_resource_raises_exception():
    """Ensure form raises exception when `formats` and 'resources` are None."""
    with pytest.raises(
        Exception, match=r"^'formats' and 'resources' can't both be None.$",
    ):
        _ = forms.ExportForm()


def test_form_init_blank_resource(
    available_formats: list[typing.Type[formats.Format]],
):
    """Ensure `file_format` choices are populated from `formats` param.

    We can remove this test when dropping support for `formats` argument.
    """
    form = forms.ExportForm(formats=available_formats)
    assert form.fields["file_format"].choices[1:] == [
        ("0", "csv"),
        ("1", "xls"),
        ("2", "xlsx"),
        ("3", "json"),
    ]


def test_form_init_one_resource(
    limited_formats_artist_resource: typing.Type[resources.CeleryResource],
):
    """Ensure `file_format` choices are populated from first resource class."""
    form = forms.ExportForm(resources=[limited_formats_artist_resource])
    assert form.fields["file_format"].choices[1:] == [
        ("0", "csv"),
        ("1", "json"),
    ]


def test_form_init_two_resources(
    limited_formats_artist_resource: typing.Type[resources.CeleryResource],
):
    """Ensure `resource` choices are populated correctly.

    Also ensure `file_format` choices are populated from first resource class.
    """
    form = forms.ExportForm(
        resources=[limited_formats_artist_resource, ArtistResourceWithM2M],
    )
    assert form.fields["resource"].choices == [
        (0, "LimitedFormatArtistResource"),
        (1, "ArtistResourceWithM2M"),
    ]
    assert form.fields["file_format"].choices[1:] == [
        ("0", "csv"),
        ("1", "json"),
    ]


def test_form_init_two_resources_and_data(
    limited_formats_artist_resource: typing.Type[resources.CeleryResource],
):
    """Ensure `file_format` choices are populated from chosen resource."""
    form = forms.ExportForm(
        resources=[limited_formats_artist_resource, ArtistResourceWithM2M],
        data={
            "resource": "1",
            "file_format": "3",
        },
    )
    assert form.fields["file_format"].choices[1:] != [
        ("0", "csv"),
        ("1", "json"),
    ]
    assert form.is_valid()
