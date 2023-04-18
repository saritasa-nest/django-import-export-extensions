import typing

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

from ... import forms, models
from .base import FormatType, ModelInfo, ResourceObj, ResourceType


class CeleryExportAdminMixin:
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
    resource_class: ResourceType = None    # type: ignore
    # export data encoding
    to_encoding = "utf-8"

    change_list_template = "admin/change_list/celery_change_list_export.html"

    # template used to display ExportForm
    celery_export_template_name = "admin/celery_export.html"

    export_status_template_name = "admin/celery_export_status.html"

    export_results_template_name = "admin/celery_export_results.html"

    # Statuses that should be displayed on 'results' page
    export_results_statuses = models.ExportJob.export_finished_statuses

    @property
    def model_info(self) -> ModelInfo:
        """Get info of exported model."""
        return ModelInfo(
            meta=self.model._meta,
        )

    def get_export_resource_kwargs(
        self,
        request: WSGIRequest,
        *args,
        **kwargs,
    ) -> dict[str, typing.Any]:
        """Get kwargs for export resource."""
        return self.get_resource_kwargs(request, *args, **kwargs)

    def get_resource_kwargs(
        self,
        request: WSGIRequest,
        *args,
        **kwargs,
    ) -> dict[str, typing.Any]:
        """Get common resource kwargs."""
        return {}

    def get_resource_class(self) -> ResourceType:
        """Get resource class."""
        return self.resource_class

    def get_export_resource_class(self) -> ResourceType:
        """Return ResourceClass to use for export."""
        return self.get_resource_class()

    def get_export_formats(self) -> list[FormatType]:
        """Get supported export formats."""
        return [
            export_format for export_format in
            self.get_resource_class().get_supported_formats()
            if export_format().can_export()
        ]

    def get_export_data(
        self,
        resource: ResourceObj,
        file_format: FormatType,
        queryset,
        *args,
        **kwargs,
    ):
        """Return file_format representation for given queryset."""
        data = resource.export(queryset, *args, **kwargs)
        export_data = file_format().export_data(data)
        return export_data

    def get_context_data(
        self,
        request: WSGIRequest,
        **kwargs,
    ) -> dict[str, typing.Any]:
        """Get context data."""
        return {}

    def get_urls(self):
        """Return list of urls.

        /<model>/<export>/:
            ExportForm ('export_action' method)
        /<model>/<export>/<ID>/:
            status of ExportJob and progress bar ('export_job_status_view')
        /<model>/<export>/<ID>/results/:
            table with export results (errors)

        """
        urls = super().get_urls()
        export_urls = [
            re_path(
                r"^celery-export/$",
                self.admin_site.admin_view(self.celery_export_action),
                name=f"{self.model_info.app_model_name}_celery_export",
            ),
            re_path(
                r"^celery-export/(?P<job_id>\d+)/$",
                self.admin_site.admin_view(self.export_job_status_view),
                name=(
                    f"{self.model_info.app_model_name}"
                    f"_celery_export_job_status"
                ),
            ),
            re_path(
                r"^celery-export/(?P<job_id>\d+)/results/$",
                self.admin_site.admin_view(
                    self.export_job_results_view,
                ),
                name=(
                    f"{self.model_info.app_model_name}"
                    f"_celery_export_job_results"
                ),
            ),
        ]
        return export_urls + urls

    def celery_export_action(self, request, *args, **kwargs):
        """Show and handle export.

        GET: show export form with format_type input
        POST: create ExportJob instance and redirect to it's status

        """
        context = self.get_context_data(request)

        formats = self.get_export_formats()
        form = forms.ExportForm(
            formats,
            request.POST or None,
        )
        is_valid_post_request = request.method == "POST" and form.is_valid()
        # Allows to get resource_kwargs passed in a form
        if is_valid_post_request:
            kwargs.update(dict(form=form))

        resource_kwargs = self.get_export_resource_kwargs(
            request=request,
            *args,
            **kwargs,
        )
        resource = self.get_export_resource_class()(**resource_kwargs)
        if is_valid_post_request:
            file_format = formats[int(form.cleaned_data["file_format"])]
            # create ExportJob and redirect to page with it's status
            job = self.create_export_job(
                request=request,
                resource_class=resource.__class__,
                resource_kwargs=resource_kwargs,
                file_format=file_format,
            )
            return self._redirect_to_export_status_page(
                request=request,
                job=job,
            )

        # GET: display Export Form
        context.update(self.admin_site.each_context(request))

        context["title"] = _("Export")
        context["form"] = form
        context["opts"] = self.model_info.meta
        context["fields"] = [
            file_format.column_name
            for file_format in resource.get_user_visible_fields()
        ]

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
        resource_class: ResourceType,
        resource_kwargs: dict[str, typing.Any],
        file_format: FormatType,
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
            f"admin:{self.model_info.app_model_name}_celery_export_job_status"
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
            f"admin:{self.model_info.app_model_name}_celery_export_job_results"
        )
        url = reverse(url_name, kwargs=dict(job_id=job.id))
        query = request.GET.urlencode()
        if query:
            url = f"{url}?{query}"
        return HttpResponseRedirect(redirect_to=url)
