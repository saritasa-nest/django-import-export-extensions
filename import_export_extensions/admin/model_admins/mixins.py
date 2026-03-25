import typing

from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import URLPattern, re_path, reverse
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

from ...models import ImportJob
from ...models.core import BaseJob


class BaseImportExportJobAdminMixin:
    """Mixin provides common methods for ImportJob and ExportJob admins."""

    change_form_template = (
        "admin/import_export_extensions/job/change_form.html"
    )

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

    def _model(self, obj: BaseJob) -> str:
        """Add `model` field of import/export job."""
        try:
            resource_class = import_string(obj.resource_path)
            model = resource_class.Meta.model._meta.verbose_name_plural
        # In case resource has no Meta or model we need to catch AttributeError
        except (ImportError, AttributeError):  # pragma: no cover
            model = _("Unknown")
        return model

    _model.short_description = _("Model")

    def get_from_content_type(
        self,
        obj: BaseJob,
    ) -> ContentType | None:  # pragma: no cover
        """Shortcut to get object from content_type."""
        content_type = obj.resource_kwargs.get("content_type")
        obj_id = obj.resource_kwargs.get("object_id")

        if content_type and obj_id:
            content_type = ContentType.objects.get(id=content_type)
            return content_type.model_class().objects.filter(id=obj_id).first()
        return None

    def render_change_form(
        self,
        request: WSGIRequest,
        context: dict[str, typing.Any],
        *args,
        **kwargs,
    ) -> HttpResponse:
        """Add `IMPORT_EXPORT_RERUN_ENABLED` to context."""
        context["IMPORT_EXPORT_RERUN_ENABLED"] = (
            settings.IMPORT_EXPORT_RERUN_ENABLED
        )
        return super().render_change_form(request, context, *args, **kwargs) # type: ignore[misc]

    def get_urls(self) -> list[URLPattern]:
        """Add url to re-run job.

        - /admin/import_export_extensions/exportjob/<job_id>/re-run/
        - /admin/import_export_extensions/importjob/<job_id>/re-run/

        """
        urls = super().get_urls() # type: ignore[misc]
        custom_urls = []

        if settings.IMPORT_EXPORT_RERUN_ENABLED:
            custom_urls += [
                re_path(
                    r"^(?P<job_id>\d+)/re-run/$",
                    self.admin_site.admin_view(self.rerun),
                    name=f"{self.model._meta.app_label}_{self.model._meta.model_name}_rerun",
                ),
            ]

        return custom_urls + urls

    def rerun(self, request: WSGIRequest, job_id: int) -> HttpResponse:
        """Rerun job."""
        obj = self.get_object(request, job_id)
        obj.rerun()
        self.message_user(
            request,
            _("Re-run job"),
            messages.SUCCESS,
        )

        if isinstance(obj, ImportJob):
            target_meta = obj.resource.Meta.model._meta
            url = reverse(
                f"admin:{target_meta.app_label}_{target_meta.model_name}_import_job_results",
                kwargs={"job_id": obj.id},
            )
        else:
            url = reverse(
                f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change",
                kwargs={"object_id": obj.pk},
            )

        return HttpResponseRedirect(url)
