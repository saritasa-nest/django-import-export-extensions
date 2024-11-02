import typing

from import_export import admin as import_export_admin

from . import types


class BaseCeleryImportExportAdminMixin(
    import_export_admin.ImportExportMixinBase,
):
    """Extend base mixin with common logic for import/export."""

    @property
    def model_info(self) -> types.ModelInfo:
        """Get info of model."""
        return types.ModelInfo(
            meta=self.model._meta,
        )

    def get_context_data(self, **kwargs) -> dict[str, typing.Any]:
        """Get context data."""
        return {}
