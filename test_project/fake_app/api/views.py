from import_export_extensions.api import views

from ..resources import SimpleArtistResource


class ArtistExportViewSet(views.ExportJobForUserViewSet):
    """Simple ViewSet for exporting Artist model."""

    resource_class = SimpleArtistResource

class ArtistImportViewSet(views.ImportJobForUserViewSet):
    """Simple ViewSet for importing Artist model."""

    resource_class = SimpleArtistResource
