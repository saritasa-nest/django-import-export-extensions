from django.db import models as django_models
from import_export import formats

from import_export_extensions import fields, resources, widgets

from . import filters, models


class SimpleArtistResource(resources.CeleryModelResource):
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


class ArtistResourceWithM2M(resources.CeleryModelResource):
    """Artist resource with Many2Many field."""

    filterset_class = filters.ArtistM2MFilterSet

    SUPPORTED_FORMATS = [
        formats.base_formats.CSV,
        formats.base_formats.XLS,
        formats.base_formats.XLSX,
    ]

    bands = fields.IntermediateManyToManyField(
        attribute="bands",
        column_name="Bands he played in",
        widget=widgets.IntermediateManyToManyWidget(
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

    def get_queryset(self) -> django_models.QuerySet[models.Artist]:
        """Return a queryset."""
        return (
            super()
            .get_queryset()
            .prefetch_related(
                "membership_set__band",
                "bands",
            )
        )


class BandResourceWithM2M(resources.CeleryModelResource):
    """Band resource with Many2Many field."""

    artists = fields.IntermediateManyToManyField(
        attribute="artists",
        column_name="Artists in band",
        widget=widgets.IntermediateManyToManyWidget(
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

    def get_queryset(self) -> django_models.QuerySet[models.Band]:
        """Return a queryset."""
        return (
            super()
            .get_queryset()
            .prefetch_related(
                "membership_set__artist",
                "artists",
            )
        )
