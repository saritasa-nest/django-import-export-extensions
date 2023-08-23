from .export_mixin import CeleryExportAdminMixin
from .import_mixin import CeleryImportAdminMixin


class CeleryImportExportMixin(
    CeleryImportAdminMixin,
    CeleryExportAdminMixin,
):
    """Import and export mixin."""

    # template for change_list view
    import_export_change_list_template = "admin/import_export/change_list_import_export.html"
