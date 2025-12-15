from rest_framework import mixins, serializers, viewsets

from import_export_extensions import api

from .. import models, resources


class ArtistExportViewSet(api.ExportJobForUserViewSet):
    """Simple ViewSet for exporting Artist model."""

    resource_class = resources.SimpleArtistResource
    export_ordering_fields = (
        "id",
        "name",
    )

class ArtistImportViewSet(api.ImportJobForUserViewSet):
    """Simple ViewSet for importing Artist model."""

    resource_class = resources.SimpleArtistResource

class ArtistSerializer(serializers.ModelSerializer):
    """Serializer for Artist model."""

    class Meta:
        model = models.Artist
        fields = (
            "id",
            "name",
            "instrument",
        )

class ArtistViewSet(
    api.ExportStartActionMixin,
    api.ImportStartActionMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Simple viewset for Artist model."""

    resource_class = resources.SimpleArtistResource
    queryset = models.Artist.objects.all()
    serializer_class = ArtistSerializer
    filterset_class = resources.SimpleArtistResource.filterset_class
    ordering = (
        "id",
    )
    ordering_fields = (
        "id",
        "name",
    )

class DjangoTasksArtistViewSet(
    api.ExportStartActionMixin,
    api.ImportStartActionMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):

    resource_class = resources.DjangoTasksArtisResource

    queryset = models.Artist.objects.all()
    serializer_class = ArtistSerializer
    filterset_class = resources.SimpleArtistResource.filterset_class
    ordering = (
        "id",
    )
    ordering_fields = (
        "id",
        "name",
    )
