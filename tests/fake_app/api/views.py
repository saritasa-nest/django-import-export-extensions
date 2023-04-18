from tests.fake_app.resources import SimpleArtistResource

from import_export_extensions.api import views


class ArtistExportViewSet(views.ExportJobViewSet):
    """Simple ViewSet for exporting Artist model."""
    resource_class = SimpleArtistResource


class ArtistImportViewSet(views.ImportJobViewSet):
    """Simple ViewSet for importing Artist model."""
    resource_class = SimpleArtistResource
