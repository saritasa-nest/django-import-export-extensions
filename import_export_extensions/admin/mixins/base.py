# Copyright (c) Bojan Mihelac and individual contributors.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     1. Redistributions of source code must retain the above copyright notice,
#        this list of conditions and the following disclaimer.
#
#     2. Redistributions in binary form must reproduce the above copyright
#        notice, this list of conditions and the following disclaimer in the
#        documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


import dataclasses
import typing
import warnings

from django.db.models.options import Options

from import_export.formats import base_formats
from import_export.resources import modelresource_factory

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


class BaseImportExportMixin:
    """Provide common methods for export/import mixin."""

    resource_class: ResourceType = None     # type: ignore
    resource_classes: typing.Sequence[ResourceType] = []

    def check_resource_classes(
        self, resource_classes: typing.Sequence[ResourceType],
    ):
        """Ensure `resource_classes` is subscriptable."""
        if resource_classes and not hasattr(resource_classes, "__getitem__"):
            raise Exception(
                "The resource_classes field type must be "
                "subscriptable (list, tuple, ...)",
            )

    def get_resource_classes(self) -> typing.Sequence[ResourceType]:
        """Return resource classes."""
        if self.resource_classes and self.resource_class:
            raise Exception(
                "Only one of 'resource_class' and 'resource_classes' "
                "can be set.",
            )
        if hasattr(self, "get_resource_class"):
            warnings.warn(
                "The 'get_resource_class()' method has been deprecated. "
                "Please implement the new 'get_resource_classes()' method",
                DeprecationWarning,
                stacklevel=2,
            )
            return [self.get_resource_class()]
        if self.resource_class:
            warnings.warn(
                "The 'resource_class' field has been deprecated. "
                "Please implement the new 'resource_classes' field",
                DeprecationWarning,
                stacklevel=2,
            )
        if not self.resource_classes and not self.resource_class:
            return [
                modelresource_factory(
                    self.model,
                    resource_class=resources.CeleryModelResource,
                ),
            ]
        if self.resource_classes:
            return self.resource_classes
        return [self.resource_class]

    def get_resource_kwargs(
        self, request, *args, **kwargs,
    ) -> dict[str, typing.Any]:
        """Return common resource kwargs."""
        return {}

    def get_resource_index(self, form) -> int:
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

    def get_import_resource_classes(self) -> typing.Sequence[ResourceType]:
        """Return resource classes to use for importing."""
        if hasattr(self, "get_import_resource_class"):
            warnings.warn(
                "The 'get_import_resource_class()' method has been "
                "deprecated. Please implement the new "
                "'get_import_resource_classes()' method",
                DeprecationWarning,
                stacklevel=2,
            )
            return [self.get_import_resource_class()]

        resource_classes = self.get_resource_classes()
        self.check_resource_classes(resource_classes)
        return resource_classes

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

    def get_export_resource_classes(self) -> typing.Sequence[ResourceType]:
        """Return resource classes to use for exporting."""
        if hasattr(self, "get_export_resource_class"):
            warnings.warn(
                "The 'get_export_resource_class()' method has been "
                "deprecated. Please implement the new "
                "'get_export_resource_classes()' method",
                DeprecationWarning,
                stacklevel=2,
            )
            return [self.get_export_resource_class()]

        resource_classes = self.get_resource_classes()
        self.check_resource_classes(resource_classes)
        return resource_classes

    def get_export_resource_kwargs(
        self, request, *args, **kwargs,
    ) -> dict[str, typing.Any]:
        """Return kwargs for initializing export resource."""
        return self.get_resource_kwargs(request, *args, **kwargs)

    def choose_export_resource_class(self, form) -> ResourceType:
        """Return selected resource class for exporting."""
        resource_index = self.get_resource_index(form)
        return self.get_export_resource_classes()[resource_index]
