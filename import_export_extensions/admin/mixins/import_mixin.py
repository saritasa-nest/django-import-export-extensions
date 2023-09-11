import typing

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.handlers.wsgi import WSGIRequest
from django.forms.forms import Form
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


class CeleryImportAdminMixin(
    base_mixins.BaseImportMixin,
    base_admin.ImportExportMixinBase,
):
    """Admin mixin for celery import.

    Admin import work-flow is:

    GET ``celery_import_action()`` - display form with import file input

    POST ``celery_import_action()`` - save file and create ImportJob.
        This view redirects to next view:

    GET ``celery_import_job_status_view()`` - display ImportJob status (with
        progress bar and critical errors occurred). When data parsing is
        done, redirect to next view:

    GET ``celery_import_job_results_view()`` - display rows that will be
        imported and data parse errors. If no errors - next step.
        If errors - display same form as in ``import_action()``

    POST ``celery_import_job_results_view()`` - start data importing and
        redirect back to GET ``celery_import_job_status_view()``
        with progress bar and import totals.

    """
    # Import data encoding
    from_encoding = "utf-8"

    # Statuses that should be displayed on 'results' page
    results_statuses = models.ImportJob.results_statuses

    # Template used to display ImportForm
    celery_import_template = "admin/import_export/import.html"

    # Template used to display status of import jobs
    import_status_template = "admin/import_export_extensions/celery_import_status.html"

    # template used to display results of import jobs
    import_result_template_name = "admin/import_export_extensions/celery_import_results.html"

    import_export_change_list_template = "admin/import_export/change_list_import.html"

    skip_admin_log = None
    # Copy methods of mixin from original package to reuse it here
    generate_log_entries = base_admin.ImportMixin.generate_log_entries
    get_skip_admin_log = base_admin.ImportMixin.get_skip_admin_log
    has_import_permission = base_admin.ImportMixin.has_import_permission

    @property
    def model_info(self) -> types.ModelInfo:
        """Get info of imported model."""
        return types.ModelInfo(
            meta=self.model._meta,
        )

    def get_context_data(
        self,
        request: WSGIRequest,
        **kwargs,
    ) -> dict[str, typing.Any]:
        """Get context data."""
        return {}

    def get_import_context_data(self, **kwargs):
        """Get context for import data."""
        return self.get_context_data(**kwargs)

    def get_urls(self):
        """Return list of urls.

        * /<model>/<celery-import>/:
            ImportForm ('celery_import_action' method)
        * /<model>/<celery-import>/<ID>/:
            status of ImportJob and progress bar
            ('celery_import_job_status_view')
        * /<model>/<celery-import>/<ID>/results/:
            table with import results (errors) and import confirmation
            ('celery_import_job_results_view')

        """
        urls = super().get_urls()
        import_urls = [
            re_path(
                r"^celery-import/$",
                self.admin_site.admin_view(self.celery_import_action),
                name=f"{self.model_info.app_model_name}_import",
            ),
            re_path(
                r"^celery-import/(?P<job_id>\d+)/$",
                self.admin_site.admin_view(self.celery_import_job_status_view),
                name=(
                    f"{self.model_info.app_model_name}"
                    f"_import_job_status"
                ),
            ),
            re_path(
                r"^celery-import/(?P<job_id>\d+)/results/$",
                self.admin_site.admin_view(
                    self.celery_import_job_results_view,
                ),
                name=(
                    f"{self.model_info.app_model_name}"
                    f"_import_job_results"
                ),
            ),
        ]
        return import_urls + urls

    def celery_import_action(
        self,
        request: WSGIRequest,
        *args,
        **kwargs,
    ):
        """Show and handle ImportForm.

        GET:
            show import form with data_file input form
        POST:
            create ImportJob instance and redirect to it's status

        """
        if not self.has_import_permission(request):
            raise PermissionDenied

        context = self.get_context_data(request)
        resource_classes = self.get_import_resource_classes()

        form = base_forms.ImportForm(
            self.get_import_formats(),
            request.POST or None,
            request.FILES or None,
            resources=resource_classes,
        )
        resource_kwargs = self.get_import_resource_kwargs(request)

        if request.method == "POST" and form.is_valid():
            # create ImportJob and redirect to page with it's status
            resource_class = self.choose_import_resource_class(form)
            job = self.create_import_job(
                request=request,
                resource=resource_class(**resource_kwargs),
                form=form,
            )
            return self._redirect_to_import_status_page(
                request=request,
                job=job,
            )

        # GET: display Import Form
        resources = [
            resource_class(**resource_kwargs)
            for resource_class in resource_classes
        ]

        context.update(self.admin_site.each_context(request))

        context["title"] = _("Import")
        context["form"] = form
        context["opts"] = self.model_info.meta
        context["media"] = self.media + form.media
        context["fields_list"] = [
            (
                resource.get_display_name(),
                [f.column_name for f in resource.get_user_visible_fields()],
            )
            for resource in resources
        ]

        request.current_app = self.admin_site.name
        return TemplateResponse(
            request,
            [self.celery_import_template],
            context,
        )

    def celery_import_job_status_view(
        self,
        request: WSGIRequest,
        job_id: int,
        **kwargs,
    ) -> HttpResponse:
        """View to track import job status.

        Displays current import job status and progress (using JS + another
        view).

        If job result is ready - redirects to another page to see results.

        Also generates admin log entries if the job has `IMPORTED` status.

        """
        if not self.has_import_permission(request):
            raise PermissionDenied

        job = self.get_import_job(request, job_id)
        if job.import_status in self.results_statuses:
            if job.import_status == models.ImportJob.ImportStatus.IMPORTED:
                self.generate_log_entries(job.result, request)
            return self._redirect_to_results_page(
                request=request,
                job=job,
            )

        context = self.get_context_data(request)
        job_url = reverse("admin:import_job_progress", args=(job.id,))
        context.update(
            dict(
                title=_("Import status"),
                opts=self.model_info.meta,
                import_job=job,
                import_job_url=job_url,
            ),
        )
        request.current_app = self.admin_site.name
        return TemplateResponse(
            request=request,
            template=[self.import_status_template],
            context=context,
        )

    def celery_import_job_results_view(
        self,
        request: WSGIRequest,
        job_id: int,
        *args,
        **kwargs,
    ) -> HttpResponse:
        """Display table with import results and import confirm form.

        GET-request:
            * show row results
            * if data valid - show import confirmation form
            * if data invalid - show ImportForm for uploading other file

        POST-request:
            * start data importing if data is correct

        """
        if not self.has_import_permission(request):
            raise PermissionDenied

        job = self.get_import_job(request=request, job_id=job_id)
        if job.import_status not in self.results_statuses:
            return self._redirect_to_import_status_page(
                request=request,
                job=job,
            )

        context = self.get_context_data(request=request)

        if request.method == "GET":
            # GET request, show parse results
            result = job.result
            context["import_job"] = job
            context["result"] = result
            context["title"] = _("Import results")

            if job.import_status != models.ImportJob.ImportStatus.PARSED:
                # display import form
                context["import_form"] = base_forms.ImportForm(
                    import_formats=job.resource.SUPPORTED_FORMATS,
                )
            else:
                context["confirm_form"] = Form()

            context.update(self.admin_site.each_context(request))
            context["opts"] = self.model_info.meta
            request.current_app = self.admin_site.name
            return TemplateResponse(
                request,
                [self.import_result_template_name],
                context,
            )

        # POST request. If data is invalid - error
        if job.import_status != models.ImportJob.ImportStatus.PARSED:
            return HttpResponseForbidden(
                "Data invalid, before importing data "
                "needs to be successfully parsed."
                f"Current status: {job.import_status}",
            )

        # start celery task for data importing
        job.confirm_import()
        return self._redirect_to_import_status_page(request=request, job=job)

    def create_import_job(
        self,
        request: WSGIRequest,
        form: Form,
        resource: types.ResourceObj,
    ):
        """Create and return instance of import job."""
        return models.ImportJob.objects.create(
            resource_path=resource.class_path,
            data_file=form.cleaned_data["import_file"],
            resource_kwargs=resource.resource_init_kwargs,
            created_by=request.user,
            skip_parse_step=getattr(settings, "IMPORT_EXPORT_SKIP_ADMIN_CONFIRM", False),
        )

    def get_import_job(
        self,
        request: WSGIRequest,
        job_id: int,
    ) -> models.ImportJob:
        """Get ImportJob instance.

        Raises:
            Http404

        """
        return get_object_or_404(klass=models.ImportJob, id=job_id)

    def _redirect_to_import_status_page(
        self,
        request: WSGIRequest,
        job: models.ImportJob,
    ) -> HttpResponseRedirect:
        """Shortcut for redirecting to job's status page."""
        url_name = (
            f"admin:{self.model_info.app_model_name}_import_job_status"
        )
        url = reverse(url_name, kwargs=dict(job_id=job.id))
        query = request.GET.urlencode()
        url = f"{url}?{query}" if query else url
        return HttpResponseRedirect(redirect_to=url)

    def _redirect_to_results_page(
        self,
        request: WSGIRequest,
        job: models.ImportJob,
    ) -> HttpResponseRedirect:
        """Shortcut for redirecting to job's results page."""
        url_name = (
            f"admin:{self.model_info.app_model_name}_import_job_results"
        )
        url = reverse(url_name, kwargs=dict(job_id=job.id))
        query = request.GET.urlencode()
        url = f"{url}?{query}" if query else url
        if not job.import_status == models.ImportJob.ImportStatus.PARSED:
            return HttpResponseRedirect(redirect_to=url)

        # Redirections add one by one links to `redirect_to`
        key = request.session.get("redirect_key", None)
        session = request.session
        if key:
            links = cache.get(key)
            try:
                session["redirect_to"] = links[0]
                del links[0]
                cache.set(key, links)
            except (TypeError, IndexError):
                session.pop("redirect_to", None)
                session.pop("redirect_key", None)
                cache.delete(key)

        return HttpResponseRedirect(redirect_to=url)

    def changelist_view(
        self,
        request: WSGIRequest,
        context: typing.Optional[dict[str, typing.Any]] = None,
    ):
        """Add the check for permission to changelist template context."""
        context = context or {}
        context["has_import_permission"] = self.has_import_permission(request)
        return super().changelist_view(request, context)
