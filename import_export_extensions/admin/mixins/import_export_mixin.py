from .export_mixin import ExportAdminMixin
from .import_mixin import ImportAdminMixin


class ImportExportMixin(
    ImportAdminMixin,
    ExportAdminMixin,
):
    """Import and export mixin."""

    # template for change_list view
    import_export_change_list_template = (
        "admin/import_export/change_list_import_export.html"
    )
