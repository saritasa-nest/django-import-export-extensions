import typing

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.handlers.wsgi import WSGIRequest
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

from django_object_actions import DjangoObjectActions

from ... import models


class ImportJobActionsMixin(DjangoObjectActions):
    """Logic of ImportJob object actions."""

    def cancel_import_action(
        self,
        request: WSGIRequest,
        obj: models.ImportJob,
    ):
        """Admin action for cancelling data import."""
        try:
            obj.cancel_import()
            self.message_user(request, _("Import Canceled"), messages.SUCCESS)
        except ValueError as error:
            self.message_user(request, str(error), messages.ERROR)

    cancel_import_action.label = _("Cancel data import")

    def confirm_import_action(
        self,
        request: WSGIRequest,
        obj: models.ImportJob,
    ):
        """Admin action for confirming data import."""
        try:
            obj.confirm_import()
            self.message_user(request, _("Import Confirmed"), messages.SUCCESS)
        except ValueError as error:
            self.message_user(request, str(error), messages.ERROR)

    confirm_import_action.label = _("Confirm data import")

    change_actions = (
        "cancel_import_action",
        "confirm_import_action",
    )

    def get_change_actions(
        self,
        request: WSGIRequest,
        object_id: int,
        form_url,
    ):
        """Return available object actions based on job status."""
        obj: models.ImportJob = self.get_object(request, object_id)
        if not hasattr(obj, "import_status"):
            return []
        actions = {
            models.ImportJob.ImportStatus.CREATED: ["cancel_import_action"],
            models.ImportJob.ImportStatus.PARSING: ["cancel_import_action"],
            models.ImportJob.ImportStatus.PARSED: ["confirm_import_action"],
            models.ImportJob.ImportStatus.CONFIRMED: ["cancel_import_action"],
            models.ImportJob.ImportStatus.IMPORTING: ["cancel_import_action"],
        }
        return actions.get(obj.import_status, [])


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
