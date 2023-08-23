import typing

from django.contrib.contenttypes.models import ContentType
from django.core.handlers.wsgi import WSGIRequest
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

from ... import models


class BaseImportExportJobAdminMixin:
    """Mixin provides common methods for ImportJob and ExportJob admins."""

    def has_add_permission(
        self,
        request: WSGIRequest,
        *args,
        **kwargs,
    ) -> bool:
        """Import/Export Jobs should not be created using this interface."""
        return False

    def has_delete_permission(
        self,
        request: WSGIRequest,
        *args,
        **kwargs,
    ) -> bool:
        """Import/Export Jobs should not be deleted using this interface.

        Instead, admins must cancel jobs.

        """
        return False

    def _model(self, obj: models.ImportJob) -> str:
        """Add `model` field of import/export job."""
        try:
            resource_class = import_string(obj.resource_path)
            model = resource_class.Meta.model._meta.verbose_name_plural
        # In case resource has no Meta or model we need to catch AttributeError
        except (ImportError, AttributeError):
            model = _("Unknown")
        return model

    def get_from_content_type(
        self,
        obj: typing.Union[models.ImportJob, models.ExportJob],
    ) -> typing.Union[ContentType, None]:
        """Shortcut to get object from content_type."""
        content_type = obj.resource_kwargs.get("content_type")
        obj_id = obj.resource_kwargs.get("object_id")

        if content_type and obj_id:
            content_type = ContentType.objects.get(id=content_type)
            return content_type.model_class().objects.filter(id=obj_id).first()
        return None
