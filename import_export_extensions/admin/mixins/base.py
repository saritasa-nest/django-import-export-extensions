
import dataclasses
import typing

from django.db.models.options import Options
from django.forms import Form

from import_export.formats import base_formats
from import_export.resources import modelresource_factory

from ...resources import CeleryModelResource, CeleryResource

ResourceObj = typing.Union[CeleryResource, CeleryModelResource]
ResourceType = typing.Type[ResourceObj]
FormatType = typing.Type[base_formats.Format]


@dataclasses.dataclass
class ModelInfo:
    """Contain base info about imported model."""

    meta: Options

    @property
    def name(self) -> str:
        """Get name of model."""
        return self.meta.model_name or ""

    @property
    def app_label(self) -> str:
        """App label of model."""
        return self.meta.app_label

    @property
    def app_model_name(self) -> str:
        """Return url name."""
        return f"{self.app_label}_{self.name}"


class BaseImportExportMixin:
    """Provide common methods for export/import mixin."""

    resource_classes: typing.Sequence[ResourceType] | None = None

    def get_resource_classes(self) -> tuple[ResourceType, ...]:
        """Return resource classes."""
        if self.resource_classes:
            return tuple(self.resource_classes)

        resource_class = modelresource_factory(
            self.model,
            resource_class=CeleryModelResource,
        )
        return (typing.cast(ResourceType, resource_class),)

    def get_resource_kwargs(self, *args, **kwargs) -> dict[str, typing.Any]:
        """Return common resource kwargs."""
        return {}

    def get_resource_index(self, form: Form) -> int:
        """Return selected resource index from form."""
        resource_index = 0
        if form and "resource" in form.cleaned_data:
            try:
                resource_index = int(form.cleaned_data["resource"])
            except ValueError:
                pass
        return resource_index


class BaseImportMixin(BaseImportExportMixin):
    """Base class for import mixin."""

    def get_import_resource_classes(self) -> tuple[ResourceType, ...]:
        """Return resource classes to use for importing."""
        return self.get_resource_classes()

    def get_import_resource_kwargs(
        self, request, *args, **kwargs,
    ) -> dict[str, typing.Any]:
        """Return kwargs for initializing import resource."""
        return self.get_resource_kwargs(request, *args, **kwargs)

    def choose_import_resource_class(self, form) -> ResourceType:
        """Return selected resource class for importing."""
        resource_index = self.get_resource_index(form)
        return self.get_import_resource_classes()[resource_index]


class BaseExportMixin(BaseImportExportMixin):
    """Base class for export mixin."""

    def get_export_resource_classes(self) -> tuple[ResourceType, ...]:
        """Return resource classes to use for exporting."""
        return self.get_resource_classes()

    def get_export_resource_kwargs(
        self, request, *args, **kwargs,
    ) -> dict[str, typing.Any]:
        """Return kwargs for initializing export resource."""
        return self.get_resource_kwargs(request, *args, **kwargs)

    def choose_export_resource_class(self, form) -> ResourceType:
        """Return selected resource class for exporting."""
        resource_index = self.get_resource_index(form)
        return self.get_export_resource_classes()[resource_index]
