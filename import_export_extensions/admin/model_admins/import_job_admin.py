import typing

from django.contrib import admin, messages
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import QuerySet
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import re_path
from django.utils.translation import gettext_lazy as _

from ... import models
from .. import forms
from . import mixins


class ImportJobAdmin(
    mixins.BaseImportExportJobAdminMixin,
    admin.ModelAdmin,
):
    """Admin class for debugging ImportJob."""

    form = forms.ImportJobAdminForm
    exclude = ("result",)
    list_display = (
        "id",
        "import_status",
        "_model",
        "created_by",
        "created",
        "parse_finished",
        "import_started",
        "import_finished",
    )
    list_display_links = (
        "id",
        "import_status",
        "_model",
    )
    import_job_model = models.ImportJob
    list_filter = ("import_status",)
    list_select_related = ("created_by",)
    actions = (
        "cancel_jobs",
        "confirm_jobs",
    )

    def get_queryset(self, request: WSGIRequest):
        """Override `get_queryset`.

        Do not get `result` from db because it can be rather big and is not
        used in admin.

        """
        return super().get_queryset(request).defer("result")

    def get_urls(self):
        """Add url to get current import job progress in JSON representation.

        /admin/import_export_extensions/importjob/<job_id>/progress/

        """
        urls = super().get_urls()
        import_urls = [
            re_path(
                r"^(?P<job_id>\d+)/progress/$",
                self.admin_site.admin_view(self.import_job_progress_view),
                name="import_job_progress",
            ),
        ]
        return import_urls + urls

    def import_job_progress_view(
        self,
        request: WSGIRequest,
        job_id: int,
        **kwargs,
    ) -> JsonResponse:
        """View to return ``ImportJob`` status as JSON.

        If current status is parsing/importing, view also returns job state
        and percent of completed work.

        Return:
            Response: dictionary with status (optionally, state and percent).

        """
        try:
            job: models.ImportJob = self.import_job_model.objects.get(
                id=job_id,
            )
        except self.import_job_model.DoesNotExist as error:
            return JsonResponse(dict(validation_error=error.args[0]))

        response_data = dict(status=job.import_status.title())

        if job.import_status in models.ImportJob.progress_statuses:
            percent = 0
            total = 0
            current = 0
            info = job.progress["info"]

            if info and info["total"]:
                percent = int(100 / info["total"] * info["current"])
                total = info["total"]
                current = info["current"]

            response_data.update(
                dict(
                    state=job.progress["state"],
                    percent=percent,
                    total=total,
                    current=current,
                ),
            )

        return JsonResponse(response_data)

    def get_readonly_fields(
        self,
        request: WSGIRequest,
        obj: typing.Optional[models.ImportJob] = None,
    ) -> list[str]:
        """Return readonly fields.

        Some fields are editable for new ImportJob.

        """
        readonly_fields = [
            "import_status",
            "_model",
            "created_by",
            "traceback_str",
            "_show_results",
            "_input_errors",
            "created",
            "parse_finished",
            "import_started",
            "import_finished",
        ]
        if obj:
            readonly_fields.extend(
                [
                    "resource_path",
                    "data_file",
                    "resource_kwargs",
                ],
            )

        return readonly_fields

    def _show_results(
        self,
        obj: typing.Optional[models.ImportJob] = None,
    ) -> str:
        """Show results totals.

        Example return value:
        New: 99
        Update: 1
        Delete: 0
        Skip: 0
        Error: 0

        """
        if not obj:
            return ""

        result_sections = []
        for key, value in obj.result.totals.items():
            status_template = f"{key.title()}: {value}"
            result_sections.append(status_template)

        return "\n".join(result_sections)

    _show_results.short_description = _("Parse/Import results")

    def _input_errors(self, job: models.ImportJob):
        """Render html with input errors."""
        template = "admin/import_export_extensions/import_job_results.html"
        return render_to_string(
            template,
            dict(result=job.result),
        )

    _input_errors.short_description = "Import data"
    _input_errors.allow_tags = True

    def get_fieldsets(
        self,
        request: WSGIRequest,
        obj: typing.Optional[models.ImportJob] = None,
    ):
        """Get fieldsets depending on object status."""
        status = (
            _("Status"),
            {
                "fields": (
                    "import_status",
                    "_model",
                    "created_by",
                    "created",
                    "parse_finished",
                    "import_started",
                    "import_finished",
                ),
            },
        )
        progress = (
            _("Status"),
            {
                "fields": (
                    "import_status",
                    "import_progressbar",
                ),
            },
        )
        import_params = (
            _("Import params"),
            {
                "fields": (
                    "data_file",
                    "resource_path",
                    "resource_kwargs",
                ),
                "classes": ("collapse",),
            },
        )
        traceback_ = (
            _("Traceback"),
            {
                "fields": ("traceback",),
            },
        )
        result = (
            _("Result totals"),
            {
                "fields": ("_show_results",),
                "classes": ("collapse",),
            },
        )
        data = (
            _("Importing data"),
            {
                "fields": ("_input_errors",),
                "classes": ("collapse",),
            },
        )

        if not obj:
            return [status, import_params]

        if obj.import_status == models.ImportJob.ImportStatus.CREATED:
            return [status, import_params]

        if obj.import_status in models.ImportJob.results_statuses:
            return [status, result, data, import_params]

        if obj.import_status in models.ImportJob.progress_statuses:
            return [status, progress, import_params]

        return [status, traceback_, import_params]

    @admin.action(description="Cancel selected jobs")
    def cancel_jobs(self, request: WSGIRequest, queryset: QuerySet):
        """Admin action for cancelling data import."""
        for job in queryset:
            try:
                job.cancel_import()
                self.message_user(
                    request,
                    _(f"Import of {job} canceled"),
                    messages.SUCCESS,
                )
            except ValueError as error:
                self.message_user(request, str(error), messages.ERROR)

    @admin.action(description="Confirm selected jobs")
    def confirm_jobs(self, request: WSGIRequest, queryset: QuerySet):
        """Admin action for confirming data import."""
        for job in queryset:
            try:
                job.confirm_import()
                self.message_user(
                    request,
                    _(f"Import of {job} confirmed"),
                    messages.SUCCESS,
                )
            except ValueError as error:
                self.message_user(request, str(error), messages.ERROR)


admin.site.register(models.ImportJob, ImportJobAdmin)
