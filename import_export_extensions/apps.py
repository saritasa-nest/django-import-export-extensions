import mimetypes

from django.apps import AppConfig
from django.conf import settings
from django.utils.translation import gettext_lazy as _

# Default configuration
# Maximum num of rows to be imported
DEFAULT_MAX_DATASET_ROWS = 100000


class CeleryImportExport(AppConfig):
    """Default configuration for CeleryImportExport app."""

    name = "import_export_extensions"
    verbose_name = _("Celery Import/Export")

    def ready(self):
        """Set up default settings."""
        settings.IMPORT_EXPORT_MAX_DATASET_ROWS = getattr(
            settings,
            "IMPORT_EXPORT_MAX_DATASET_ROWS",
            DEFAULT_MAX_DATASET_ROWS,
        )
        settings.MIME_TYPES_MAP = mimetypes.types_map.copy()
