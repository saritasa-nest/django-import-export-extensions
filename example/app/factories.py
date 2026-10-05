import factory
from django.core.files import base as django_files
from import_export.formats import base_formats as formats

from import_export_extensions.models import ExportJob, ImportJob

from . import models, resources


class InstrumentFactory(factory.django.DjangoModelFactory[models.Instrument]):
    """Simple factory for ``Instrument`` model."""

    title = factory.Faker("name")

    class Meta:
        model = models.Instrument


class ArtistFactory(factory.django.DjangoModelFactory[models.Artist]):
    """Simple factory for ``Artist`` model."""

    name = factory.Faker("name")
    external_id = factory.Faker("uuid4")
    instrument = factory.SubFactory(InstrumentFactory)

    class Meta:
        model = models.Artist


class BandFactory(factory.django.DjangoModelFactory[models.Band]):
    """Simple factory for ``Band`` model."""

    title = factory.Faker("company")

    class Meta:
        model = models.Band


class MembershipFactory(factory.django.DjangoModelFactory[models.Membership]):
    """Simple factory for ``Membership`` model."""

    artist = factory.SubFactory(ArtistFactory)
    band = factory.SubFactory(BandFactory)
    date_joined = factory.Faker("date")

    class Meta:
        model = models.Membership


class ArtistImportJobFactory(factory.django.DjangoModelFactory[ImportJob]):
    """Factory for creating ImportJob for Artist.

    Usage:
        ArtistImportJobFactory.create(artists=[artist1, artist2])
    """

    resource_path = "example.app.resources.SimpleArtistResource"
    resource_kwargs: dict[str, str] = {}

    class Meta:
        model = ImportJob

    class Params:
        artists: list[models.Artist] = []
        is_valid_file: bool = True

    @factory.lazy_attribute
    def data_file(self) -> django_files.File:
        """Generate `data_file` based on passed `artists`."""
        resource = resources.SimpleArtistResource()

        if not self.is_valid_file:
            # Append not existing artist with a non-existent instrument
            # to violate the not-null constraint
            self.artists.append(
                ArtistFactory.build(instrument=InstrumentFactory.build()),
            )

        dataset = resource.export(self.artists)
        export_data = formats.CSV().export_data(dataset)
        content = django_files.ContentFile(export_data)
        return django_files.File(content.file, "data.csv")


class ArtistExportJobFactory(factory.django.DjangoModelFactory[ExportJob]):
    """Factory for creating ExportJob for Artist."""

    resource_path = "example.app.resources.SimpleArtistResource"
    resource_kwargs: dict[str, str] = {}
    file_format_path = "import_export.formats.base_formats.CSV"

    class Meta:
        model = ExportJob
