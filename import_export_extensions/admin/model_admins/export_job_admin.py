
import http

from django.contrib import admin, messages
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import QuerySet
from django.http import JsonResponse
from django.urls import re_path
from django.utils.translation import gettext_lazy as _

from ... import models
from .. import forms
from . import mixins


class ExportJobAdmin(
    mixins.BaseImportExportJobAdminMixin,
    admin.ModelAdmin,
):
    """Admin class for debugging ExportJob."""

    form = forms.ExportJobAdminForm
    exclude = ("result",)
    list_display = (
        "id",
        "export_status",
        "_model",
        "export_started",
        "export_finished",
        "created",
        "created_by",
    )
    list_display_links = (
        "id",
        "export_status",
        "_model",
    )
    export_job_model = models.ExportJob
    list_filter = ("export_status",)
    list_select_related = ("created_by",)
    actions = (
        "cancel_jobs",
    )
    readonly_fields = (
        "export_status",
        "traceback",
        "file_format_path",
        "created",
        "export_started",
        "export_finished",
        "error_message",
        "_model",
        "resource_path",
        "data_file",
        "resource_kwargs",
    )

    def get_urls(self):
        """Add url to get current export job progress in JSON representation.

        /admin/import_export_extensions/exportjob/<job_id>/progress/

        """
        urls = super().get_urls()
        export_urls = [
            re_path(
                route=r"^(?P<job_id>\d+)/progress/$",
                view=self.admin_site.admin_view(self.export_job_progress_view),
                name="export_job_progress",
            ),
        ]
        return export_urls + urls

    def export_job_progress_view(
        self,
        request: WSGIRequest,
        job_id: int,
        **kwargs,
    ):
        """View to return `ExportJob` status as JSON.

        If current status is exporting, view also returns job state
        and percent of completed work.

        Return:
            Response: dictionary with status (optionally, state and percent).

        """
        try:
            job: models.ExportJob = self.export_job_model.objects.get(
                id=job_id,
            )
        except self.export_job_model.DoesNotExist as error:
            return JsonResponse(
                dict(validation_error=error.args[0]),
                status=http.HTTPStatus.NOT_FOUND,
            )

        response_data = dict(status=job.export_status.title())

        if job.export_status != models.ExportJob.ExportStatus.EXPORTING:
            return JsonResponse(response_data)

        percent = 0
        total = 0
        current = 0
        job_progress = job.progress
        progress_info = job_progress["info"]

        if progress_info and progress_info["total"]:
            total = progress_info["total"]
            current = progress_info["current"]
            percent = int(100 / total * current)

        response_data.update(
            state=job_progress["state"],
            percent=percent,
            total=total,
            current=current,
        )
        return JsonResponse(response_data)

    def get_fieldsets(
        self,
        request: WSGIRequest,
        obj: models.ExportJob,
    ):
        """Get fieldsets depending on object status."""
        status = (
            _("Status"),
            {
                "fields": (
                    "export_status",
                    "_model",
                    "created",
                    "export_started",
                    "export_finished",
                ),
            },
        )
        progress = (
            _("Status"),
            {
                "fields": (
                    "export_status",
                    "export_progressbar",
                ),
            },
        )
        export_params = (
            _("Export params"),
            {
                "fields": (
                    "resource_path",
                    "resource_kwargs",
                    "file_format_path",
                ),
                "classes": ("collapse",),
            },
        )
        traceback_fields = (
            _("Traceback"),
            {
                "fields": (
                    "error_message",
                    "traceback",
                ),
            },
        )
        result = (
            _("Export results"),
            {
                "fields": ("data_file",),
            },
        )

        if obj.export_status == models.ExportJob.ExportStatus.CREATED:
            return [status, export_params]

        if obj.export_status == models.ExportJob.ExportStatus.EXPORTED:
            return [status, result, export_params]

        if obj.export_status == models.ExportJob.ExportStatus.EXPORTING:
            return [progress, export_params]

        return [status, traceback_fields, export_params]

    @admin.action(description="Cancel selected jobs")
    def cancel_jobs(self, request: WSGIRequest, queryset: QuerySet):
        """Admin action for cancelling data export."""
        for job in queryset:
            try:
                job.cancel_export()
                self.message_user(
                    request,
                    _(f"Export of {job} canceled"),
                    messages.SUCCESS,
                )
            except ValueError as error:
                self.message_user(request, str(error), messages.ERROR)


admin.site.register(models.ExportJob, ExportJobAdmin)
