from rest_framework import (
    decorators,
    mixins,
    permissions,
    response,
    serializers,
    settings,
    throttling,
    viewsets,
)

from import_export_extensions import api

from .. import models, resources


class ArtistExportViewSet(api.ExportJobForUserViewSet):
    """Simple ViewSet for exporting Artist model."""

    resource_class = resources.SimpleArtistResource
    export_ordering_fields = (
        "id",
        "name",
    )


class BandExportViewSet(api.ExportJobForUserViewSet):
    """Simple ViewSet for exporting Band model."""

    resource_class = resources.BandResourceWithM2M
    export_ordering_fields = (
        "id",
        "title",
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


class ScopedRateThrottle(throttling.ScopedRateThrottle):
    """Custom for testing."""

    def get_rate(self) -> str:
        """Make it lazy for easier testing."""
        return settings.api_settings.DEFAULT_THROTTLE_RATES[self.scope]


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
    ordering = ("id",)
    ordering_fields = (
        "id",
        "name",
    )
    export_permission_classes = (permissions.IsAuthenticated,)

    @decorators.action(
        methods=["POST"],
        detail=False,
        export_action_name="export-m2m",
        export_action_url="export-m2m",
        is_export_action=True,
        resource_class=resources.ArtistResourceWithM2M,
        export_ordering_fields=(
            "id",
            "name",
        ),
        export_throttle_classes=(ScopedRateThrottle,),
    )
    def export_m2m(self, request, *args, **kwargs) -> response.Response:
        """Export artists with Many2Many field."""
        return self.start_export(request, *args, **kwargs)
