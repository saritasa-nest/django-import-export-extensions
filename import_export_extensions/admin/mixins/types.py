import dataclasses
import typing

from django.db.models.options import Options

from import_export.formats import base_formats

from ... import resources

ResourceObj = typing.Union[
    resources.CeleryResource,
    resources.CeleryModelResource,
]
ResourceType = typing.Type[ResourceObj]
FormatType = typing.Type[base_formats.Format]


@dataclasses.dataclass
class ModelInfo:
    """Contain base info about imported model."""

    meta: Options

    @property
    def name(self) -> str:
        """Get name of model."""
        return self.meta.model_name

    @property
    def app_label(self):
        """App label of model."""
        return self.meta.app_label

    @property
    def app_model_name(self) -> str:
        """Return url name."""
        return f"{self.app_label}_{self.name}"
