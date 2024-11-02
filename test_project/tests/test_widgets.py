import io

from django.core.files import File
from django.core.files.storage import default_storage
from django.forms import ValidationError

import pytest
import pytest_mock
from import_export.exceptions import ImportExportError
from pytest_mock import MockerFixture

from import_export_extensions.widgets import (
    FileWidget,
    IntermediateManyToManyWidget,
)

from ..fake_app.factories import (
    ArtistFactory,
    ArtistImportJobFactory,
    BandFactory,
    MembershipFactory,
)
from ..fake_app.models import Band, Membership


@pytest.fixture
def import_file():
    """Prepare import file from import job."""
    import_job = ArtistImportJobFactory.build(artists=[ArtistFactory()])
    return import_job.data_file


def test_get_related_instance(membership: Membership):
    """Test private method returns instance of related model.

    For example, if we render Artist.bands, for specified Membership
    instance this method should return related Band object

    """
    widget = IntermediateManyToManyWidget(
        rem_model=Band,
        instance_separator=";",
    )
    related_instance = widget._get_related_instance(membership)
    assert related_instance == membership.band


def test_render_instance_no_extra(membership: Membership):
    """Test no extra fields from relation are rendered.

    I.e. just ``Band.pk`` should be in result
    """
    widget = IntermediateManyToManyWidget(
        rem_model=Band,
        instance_separator=";",
    )

    expected_value = str(membership.band.id)
    result_value = widget.render_instance(membership, membership.band)

    assert expected_value == result_value


def test_render_instance_extra_fields(membership: Membership):
    """Test widget with `extra_fields` renders extra fields."""
    widget = IntermediateManyToManyWidget(
        rem_model=Band,
        extra_fields=["date_joined"],
        instance_separator=";",
    )
    expected_value = f"{membership.band.pk}:{membership.date_joined}"
    result_value = widget.render_instance(membership, membership.band)
    assert expected_value == result_value


def test_render_instance_not_pk(membership: Membership):
    """Test choosing field to render using `rem_field` widget param.

    I.e. if we want to render not just Band.id, but it's title

    """
    widget = IntermediateManyToManyWidget(
        rem_model=Band,
        rem_field="title",
        instance_separator=";",
    )
    expected_value = str(membership.band.title)
    result_value = widget.render_instance(membership, membership.band)

    assert expected_value == result_value


def test_render_few_instances(membership: Membership):
    """Ensure few instances are rendered using separators."""
    membership2 = MembershipFactory(artist=membership.artist)

    expected_value = (
        f"{membership.band.pk}:{membership.date_joined};"
        f"{membership2.band.pk}:{membership2.date_joined}"
    )
    widget = IntermediateManyToManyWidget(
        rem_model=Band,
        extra_fields=["date_joined"],
        instance_separator=";",
    )
    result_value = widget.render(Membership.objects.all(), membership.artist)

    assert expected_value == result_value


def test_clean_one_instance_by_pk(membership: Membership):
    """Ensure correct data cleaned when just `pk` rendered.

    Should be returned:
    {
        'object': <Band object>,
        'properties': {}
    }

    """
    raw_data = str(membership.band.id)
    widget = IntermediateManyToManyWidget(
        rem_model=Band,
        instance_separator=";",
    )
    widget_data = widget.clean_instance(raw_data)

    assert len(widget_data) == 1

    result = widget_data[0]
    assert "object" in result
    assert "properties" in result
    assert result["object"] == membership.band


def test_clean_one_instance_by_not_pk(membership: Membership):
    """Ensure correct data cleaned when saved just other field.

    Should be returned:
    {
        'object': <Band object>,
        'properties': {}
    }

    """
    raw_data = str(membership.band.title)
    widget = IntermediateManyToManyWidget(
        rem_model=Band,
        rem_field="title",
        instance_separator=";",
    )
    widget_data = widget.clean_instance(raw_data)
    assert len(widget_data) == 1

    result = widget_data[0]
    assert result["object"] == membership.band


def test_clean_one_instance_extra_properties(membership: Membership):
    """Ensure correct data cleaned when saved just other field.

    Should be returned:
    {
        'object': <Band object>,
        'properties': {'date_joined': '1990-12-12'}
    }

    """
    raw_data = f"{membership.band.pk}:{membership.date_joined}"
    widget = IntermediateManyToManyWidget(
        rem_model=Band,
        extra_fields=["date_joined"],
        instance_separator=";",
    )
    widget_data = widget.clean_instance(raw_data)

    assert len(widget_data) == 1

    result = widget_data[0]
    assert result["object"] == membership.band
    assert result["properties"]["date_joined"] == str(membership.date_joined)


def test_clean_one_instance_if_in_db_few_with_same_attr():
    """Test few objects will be returned if they have same `rem_field` value.

    Ensure if there are few instances with same value of `rem_field`
    then `clean_instance` returns few objects

    """
    band_1 = BandFactory(title="Band")
    band_2 = BandFactory(title="Band")

    raw_data = f"{band_1.title}"
    widget = IntermediateManyToManyWidget(
        rem_model=Band,
        rem_field="title",
        instance_separator=";",
    )
    result = widget.clean_instance(raw_data)

    assert len(result) == 2
    assert {item["object"] for item in result} == {band_1, band_2}


def test_clean_if_in_db_few_with_same_attr():
    """Test clean method returns unique objects with same attr.

    Ensure if there are few instances with same value of `rem_field`
    then `clean` doesn't return few same objects

    """
    band_1 = BandFactory(title="Band")
    band_2 = BandFactory(title="Band")

    raw_data = f"{band_1.title};{band_2.title}"

    widget = IntermediateManyToManyWidget(
        rem_model=Band,
        rem_field="title",
        instance_separator=";",
    )

    result = widget.clean(raw_data)

    assert len(result) == 2
    assert {item["object"] for item in result} == {band_1, band_2}


def test_clean_nonexistent_relations():
    """Test raise `ValueError` if we try to import nonexistent relations."""
    raw_data = "Some band title"
    widget = IntermediateManyToManyWidget(
        rem_model=Band,
        rem_field="title",
        instance_separator=";",
    )
    with pytest.raises(ValueError, match="import invalid values"):
        widget.clean(raw_data)


def test_clean_ignore_blank_instances():
    """Test `clean` method ignore empty strings inside document cell.

    Also check that strings which contain only whitespaces will be ignored.

    """
    widget = IntermediateManyToManyWidget(
        rem_model=Band,
        rem_field="title",
        instance_separator=";",
    )
    raw_data = (
        f"\n\n{BandFactory().title}\n \n;   {BandFactory().title}\n  \n "
    )
    result = widget.clean(raw_data)

    # ensure that there are no exceptions raised by clean and it
    # returns two instances in result
    assert len(result) == 2


def test_clean_extra_properties_with_leading_and_trailing_spaces(
    membership: Membership,
):
    """Test clean extra properties with extra whitespaces.

    Ensure that extra properties determined correctly if string
    contains extra separate characters and whitespaces.

    """
    raw_data = f"   {membership.band.pk} :  {membership.date_joined} "
    widget = IntermediateManyToManyWidget(
        rem_model=Band,
        extra_fields=["date_joined"],
        instance_separator=";",
    )

    widget_data = widget.clean_instance(raw_data)
    assert len(widget_data) == 1

    result = widget_data[0]
    assert result["object"] == membership.band
    assert result["properties"]["date_joined"] == str(membership.date_joined)


def test_clean_extra_properties_with_blank_property_value(
    membership: Membership,
):
    """Test cleaning blank extra properties.

    Ensure that extra_property would be ignored if it hasn't
    value in imported document

    """
    raw_data = f"{membership.band.pk}:"
    widget = IntermediateManyToManyWidget(
        rem_model=Band,
        extra_fields=["date_joined"],
        instance_separator=";",
    )

    widget_data = widget.clean_instance(raw_data)
    result = widget_data[0]

    assert result["object"] == membership.band
    assert "date_joined" not in result


def test_clean_extra_properties_with_too_many_prop_separators(
    membership: Membership,
):
    """Test raise exception if data contains too many property separators."""
    raw_data = f"{membership.band.pk} :: : {membership.date_joined}"
    widget = IntermediateManyToManyWidget(
        rem_model=Band,
        extra_fields=["date_joined"],
        instance_separator=";",
    )

    with pytest.raises(ImportExportError):
        widget.clean_instance(raw_data)


def test_render_empty_values(membership: Membership):
    """Check empty values rendered when `skip_empty` set to False."""
    MembershipFactory(band__title="")
    MembershipFactory(band__title="Band")
    separator = ";"

    expected_result = separator.join(
        membership.band.title for membership in Membership.objects.all()
    )

    widget = IntermediateManyToManyWidget(
        rem_model=Band,
        rem_field="title",
        render_empty=True,
        instance_separator=separator,
    )
    result = widget.render(Membership.objects.all(), membership.band)

    assert expected_result == result


@pytest.mark.parametrize(
    argnames="rem_field_lookup",
    argvalues=[
        "regex",
        "icontains",
    ],
)
def test_intermediate_widget_filter_with_lookup(rem_field_lookup: str):
    """Test widget filter rem model with lookup."""
    founded_band = BandFactory(title="In result band")
    ignored_band = BandFactory(title="This band will be ignored")

    widget = IntermediateManyToManyWidget(
        rem_model=Band,
        rem_field="title",
        rem_field_lookup=rem_field_lookup,
        instance_separator=";",
    )
    result = widget.filter_instances(founded_band.title)

    assert len(result) == 1
    assert founded_band in result
    assert ignored_band not in result


def test_file_widget_render_link(import_file):
    """Test FileWidget `render` method."""
    widget = FileWidget(
        filename="test_widget",
    )
    result = widget.render(import_file)

    assert import_file.url in result


def test_file_widget_render_link_for_non_local_env(
    import_file,
    mocker: pytest_mock.MockerFixture,
):
    """Test FileWidget `render` method."""
    widget = FileWidget(filename="test_widget")
    mocker.patch.object(
        widget,
        "_get_default_storage",
        return_value="non_local_storage",
    )
    result = widget.render(import_file)

    assert import_file.url == result


def test_file_widget_clean_url():
    """Test FileWidget `clean` method."""
    filename = default_storage.save("original", File(io.BytesIO(b"testvalue")))
    widget = FileWidget(filename="imported_file")
    cleaned_result = widget.clean(f"http://localhost/media/{filename}")

    assert cleaned_result == filename


def test_file_widget_clean_with_invalid_file_path():
    """Test that FileWidget.clean raise error with invalid file path."""
    widget = FileWidget(filename="imported_file")
    with pytest.raises(ValidationError, match="Invalid file path"):
        widget.clean("invalid_value")


def test_file_widget_clean_non_existed_url(mocker: MockerFixture):
    """Check FileWidget `clean` method with downloading new file."""
    response = mocker.MagicMock()
    response.content = b"testbytest"

    mocker.patch("requests.get", return_value=response)
    mocker.patch.object(
        default_storage,
        "exists",
        return_value=False,
    )

    widget = FileWidget(filename="import_file")
    cleaned_result = widget.clean(value="http://testdownload.org/file.csv")
    assert isinstance(cleaned_result, File)


def test_file_widget_render_none():
    """Test file widget render return None if no value provided."""
    widget = FileWidget(filename="import_file")
    assert widget.render(None) is None


def test_file_widget_clean_none():
    """Test file widget clean return None if no value provided."""
    widget = FileWidget(filename="import_file")
    assert widget.clean(None) is None
