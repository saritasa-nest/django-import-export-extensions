from import_export_extensions.fields import IntermediateManyToManyField
from import_export_extensions.resources import CeleryModelResource
from import_export_extensions.widgets import IntermediateManyToManyWidget

from .filters import ArtistFilterSet
from .models import Artist, Band


class SimpleArtistResource(CeleryModelResource):
    """Artist resource with simple fields."""

    filterset_class = ArtistFilterSet

    class Meta:
        model = Artist
        clean_model_instances = True
        fields = [
            "id",
            "name",
            "instrument",
        ]


class ArtistResourceWithM2M(CeleryModelResource):
    """Artist resource with Many2Many field."""

    bands = IntermediateManyToManyField(
        attribute="bands",
        column_name="Bands he played in",
        widget=IntermediateManyToManyWidget(
            rem_model=Band,
            rem_field="title",
            extra_fields=["date_joined"],
            instance_separator=";",
        ),
    )

    class Meta:
        model = Artist
        clean_model_instances = True
        fields = ["id", "name", "bands", "instrument"]
