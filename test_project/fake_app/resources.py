from import_export import formats

from import_export_extensions.fields import IntermediateManyToManyField
from import_export_extensions.resources import CeleryModelResource
from import_export_extensions.widgets import IntermediateManyToManyWidget

from . import filters, models


class SimpleArtistResource(CeleryModelResource):
    """Artist resource with simple fields."""

    filterset_class = filters.ArtistFilterSet

    class Meta:
        model = models.Artist
        import_id_fields = ["external_id"]
        clean_model_instances = True
        fields = [
            "id",
            "external_id",
            "name",
            "instrument",
        ]


class ArtistResourceWithM2M(CeleryModelResource):
    """Artist resource with Many2Many field."""

    filterset_class = filters.ArtistM2MFilterSet

    SUPPORTED_FORMATS = [
        formats.base_formats.CSV,
        formats.base_formats.XLS,
        formats.base_formats.XLSX,
    ]

    bands = IntermediateManyToManyField(
        attribute="bands",
        column_name="Bands he played in",
        widget=IntermediateManyToManyWidget(
            rem_model=models.Band,
            rem_field="title",
            extra_fields=["date_joined"],
            instance_separator=";",
        ),
    )

    class Meta:
        model = models.Artist
        clean_model_instances = True
        fields = ["id", "name", "bands", "instrument"]

    def get_queryset(self):
        """Return a queryset."""
        return (
            super()
            .get_queryset()
            .prefetch_related(
                "membership_set__band",
                "bands",
            )
        )


class BandResourceWithM2M(CeleryModelResource):
    """Band resource with Many2Many field."""

    artists = IntermediateManyToManyField(
        attribute="artists",
        column_name="Artists in band",
        widget=IntermediateManyToManyWidget(
            rem_model=models.Artist,
            rem_field="name",
            extra_fields=["date_joined"],
            instance_separator=";",
        ),
    )

    class Meta:
        model = models.Band
        clean_model_instances = True
        fields = ["id", "title", "artists"]

    def get_queryset(self):
        """Return a queryset."""
        return (
            super()
            .get_queryset()
            .prefetch_related(
                "membership_set__artist",
                "artists",
            )
        )
