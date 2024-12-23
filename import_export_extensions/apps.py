import mimetypes

from django.apps import AppConfig
from django.conf import settings
from django.utils.translation import gettext_lazy as _

# Default configuration
# Maximum num of rows to be imported
DEFAULT_MAX_DATASET_ROWS = 100000
# After how many imported/exported rows celery task status will be updated
DEFAULT_STATUS_UPDATE_ROW_COUNT = 100


class CeleryImportExport(AppConfig):
    """Default configuration for CeleryImportExport app."""

    name = "import_export_extensions"
    verbose_name = _("Celery Import/Export")
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        """Set up default settings."""
        settings.IMPORT_EXPORT_MAX_DATASET_ROWS = getattr(
            settings,
            "IMPORT_EXPORT_MAX_DATASET_ROWS",
            DEFAULT_MAX_DATASET_ROWS,
        )
        settings.MIME_TYPES_MAP = mimetypes.types_map.copy()
        settings.STATUS_UPDATE_ROW_COUNT = getattr(
            settings,
            "STATUS_UPDATE_ROW_COUNT",
            DEFAULT_STATUS_UPDATE_ROW_COUNT,
        )
