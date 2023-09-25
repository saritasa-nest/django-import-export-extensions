import typing

from django.core.exceptions import PermissionDenied
from django.core.handlers.wsgi import WSGIRequest
from django.http import (
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import re_path, reverse
from django.utils.translation import gettext_lazy as _

from import_export import admin as base_admin
from import_export import forms as base_forms
from import_export import mixins as base_mixins

from ... import models
from . import types


class CeleryExportAdminMixin(
    base_mixins.BaseExportMixin,
    base_admin.ImportExportMixinBase,
):
    """Admin mixin for celery export.

    Admin export work-flow is:
        GET `celery_export_action()` - display form with format type input

        POST `celery_export_action()` - create ExportJob and starts data export
            This view redirects to next view:

        GET `celery_export_job_status_view()` - display ExportJob status (with
            progress bar). When data exporting is done, redirect to next view:

        GET `celery_export_job_results_view()` - display export results. If no
            errors - success message and link to the file with exported data.
            If errors - traceback and error message.

    """
    # export data encoding
    to_encoding = "utf-8"

    # template used to display ExportForm
    celery_export_template_name = "admin/import_export/export.html"

    export_status_template_name = "admin/import_export_extensions/celery_export_status.html"

    export_results_template_name = "admin/import_export_extensions/celery_export_results.html"

    import_export_change_list_template = "admin/import_export/change_list_export.html"

    # Statuses that should be displayed on 'results' page
    export_results_statuses = models.ExportJob.export_finished_statuses

    # Copy methods of mixin from original package to reuse it here
    has_export_permission = base_admin.ExportMixin.has_export_permission

    @property
    def model_info(self) -> types.ModelInfo:
        """Get info of exported model."""
        return types.ModelInfo(
            meta=self.model._meta,
        )

    def get_export_resource_kwargs(self, request, *args, **kwargs):
        """Provide escape settings to resource kwargs."""
        kwargs = super().get_export_resource_kwargs(request, *args, **kwargs)
        kwargs.update({
            "escape_html": self.should_escape_html,
            "escape_formulae": self.should_escape_formulae,
        })
        return kwargs

    def get_context_data(
        self,
        request: WSGIRequest,
        **kwargs,
    ) -> dict[str, typing.Any]:
        """Get context data."""
        return {}

    def get_urls(self):
        """Return list of urls.

        /<model/celery-export/:
            ExportForm ('export_action' method)
        /<model>/celery-export/<ID>/:
            status of ExportJob and progress bar ('export_job_status_view')
        /<model>/celery-export/<ID>/results/:
            table with export results (errors)

        """
        urls = super().get_urls()
        export_urls = [
            re_path(
                r"^celery-export/$",
                self.admin_site.admin_view(self.celery_export_action),
                name=f"{self.model_info.app_model_name}_export",
            ),
            re_path(
                r"^celery-export/(?P<job_id>\d+)/$",
                self.admin_site.admin_view(self.export_job_status_view),
                name=(
                    f"{self.model_info.app_model_name}"
                    f"_export_job_status"
                ),
            ),
            re_path(
                r"^celery-export/(?P<job_id>\d+)/results/$",
                self.admin_site.admin_view(
                    self.export_job_results_view,
                ),
                name=(
                    f"{self.model_info.app_model_name}"
                    f"_export_job_results"
                ),
            ),
        ]
        return export_urls + urls

    def celery_export_action(self, request, *args, **kwargs):
        """Show and handle export.

        GET: show export form with format_type input
        POST: create ExportJob instance and redirect to it's status

        """
        if not self.has_export_permission(request):
            raise PermissionDenied

        formats = self.get_export_formats()
        form = base_forms.ExportForm(
            formats,
            request.POST or None,
            resources=self.get_export_resource_classes(),
        )
        resource_kwargs = self.get_export_resource_kwargs(
            request=request,
            *args,
            **kwargs,
        )
        if request.method == "POST" and form.is_valid():
            file_format = formats[int(form.cleaned_data["file_format"])]
            # create ExportJob and redirect to page with it's status
            job = self.create_export_job(
                request=request,
                resource_class=self.choose_export_resource_class(form),
                resource_kwargs=resource_kwargs,
                file_format=file_format,
            )
            return self._redirect_to_export_status_page(
                request=request,
                job=job,
            )

        # GET: display Export Form
        context = self.get_context_data(request)
        context.update(self.admin_site.each_context(request))

        context["title"] = _("Export")
        context["form"] = form
        context["opts"] = self.model_info.meta
        request.current_app = self.admin_site.name

        return TemplateResponse(
            request=request,
            template=[self.celery_export_template_name],
            context=context,
        )

    def export_job_status_view(
        self,
        request: WSGIRequest,
        job_id: int,
        **kwargs,
    ) -> HttpResponse:
        """View to track export job status.

        Displays current export job status and progress (using JS + another
        view).

        If job result is ready - redirects to another page to see results.

        """
        if not self.has_export_permission(request):
            raise PermissionDenied

        job = self.get_export_job(request=request, job_id=job_id)
        if job.export_status in self.export_results_statuses:
            return self._redirect_to_export_results_page(
                request=request,
                job=job,
            )

        context = self.get_context_data(request)
        job_url = reverse("admin:export_job_progress", args=(job.id,))

        context["title"] = _("Export status")
        context["opts"] = self.model_info.meta
        context["export_job"] = job
        context["export_job_url"] = job_url
        request.current_app = self.admin_site.name
        return TemplateResponse(
            request=request,
            template=[self.export_status_template_name],
            context=context,
        )

    def export_job_results_view(
        self,
        request: WSGIRequest,
        job_id: int,
        *args,
        **kwargs,
    ) -> HttpResponse:
        """Display export results.

        GET-request:
            * show message
            * if no errors - show file link
            * if errors - show traceback and error

        """
        if not self.has_export_permission(request):
            raise PermissionDenied

        job = self.get_export_job(request=request, job_id=job_id)
        if job.export_status not in self.export_results_statuses:
            return self._redirect_to_export_status_page(
                request=request,
                job=job,
            )

        context = self.get_context_data(request)

        if request.method != "GET":
            return HttpResponseForbidden()

        # GET request, show export results
        context["title"] = _("Export results")
        context["opts"] = self.model._meta
        context["export_job"] = job
        context["result"] = job.export_status

        return TemplateResponse(
            request=request,
            template=[self.export_results_template_name],
            context=context,
        )

    def create_export_job(
        self,
        request: WSGIRequest,
        resource_class: types.ResourceType,
        resource_kwargs: dict[str, typing.Any],
        file_format: types.FormatType,
    ) -> models.ExportJob:
        """Create and return instance of export job with chosen format."""
        job = models.ExportJob.objects.create(
            resource_path=resource_class.class_path,
            resource_kwargs=resource_kwargs,
            file_format_path=".".join(
                [
                    file_format.__module__,
                    file_format.__name__,
                ],
            ),
        )
        return job

    def get_export_job(
        self,
        request: WSGIRequest,
        job_id: int,
    ) -> models.ExportJob:
        """Get ExportJob instance.

        Raises:
            Http404

        """
        return get_object_or_404(models.ExportJob, id=job_id)

    def _redirect_to_export_status_page(
        self,
        request: WSGIRequest,
        job: models.ExportJob,
    ) -> HttpResponse:
        """Shortcut for redirecting to job's status page."""
        url_name = (
            f"admin:{self.model_info.app_model_name}_export_job_status"
        )
        url = reverse(url_name, kwargs=dict(job_id=job.id))
        query = request.GET.urlencode()
        if query:
            url = f"{url}?{query}"
        return HttpResponseRedirect(redirect_to=url)

    def _redirect_to_export_results_page(
        self,
        request: WSGIRequest,
        job: models.ExportJob,
    ) -> HttpResponse:
        """Shortcut for redirecting to job's results page."""
        url_name = (
            f"admin:{self.model_info.app_model_name}_export_job_results"
        )
        url = reverse(url_name, kwargs=dict(job_id=job.id))
        query = request.GET.urlencode()
        if query:
            url = f"{url}?{query}"
        return HttpResponseRedirect(redirect_to=url)

    def changelist_view(
        self,
        request: WSGIRequest,
        context: typing.Optional[dict[str, typing.Any]] = None,
    ):
        """Add the check for permission to changelist template context."""
        context = context or {}
        context["has_export_permission"] = True
        return super().changelist_view(request, context)
