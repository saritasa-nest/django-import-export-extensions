import typing

from django.conf import settings
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

from import_export import admin as import_export_admin
from import_export import mixins as import_export_mixins
from import_export import resources as import_export_resources
from import_export.forms import ConfirmImportForm, ImportForm

from ... import models
from ..forms import ForceImportForm
from . import base_mixin, types


class CeleryImportAdminMixin(
    import_export_mixins.BaseImportMixin,
    base_mixin.BaseCeleryImportExportAdminMixin,
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

    import_form_class: type[ImportForm] = ForceImportForm
    confirm_form_class: type[ConfirmImportForm] = ConfirmImportForm

    # Statuses that should be displayed on 'results' page
    results_statuses = models.ImportJob.results_statuses

    # Template used to display ImportForm
    celery_import_template = "admin/import_export/import.html"

    # Template used to display status of import jobs
    import_status_template = (
        "admin/import_export_extensions/celery_import_status.html"
    )

    # template used to display results of import jobs
    import_result_template_name = (
        "admin/import_export_extensions/celery_import_results.html"
    )

    import_export_change_list_template = (
        "admin/import_export/change_list_import.html"
    )

    skip_admin_log = None
    # Copy methods of mixin from original package to reuse it here
    generate_log_entries = import_export_admin.ImportMixin.generate_log_entries
    get_skip_admin_log = import_export_admin.ImportMixin.get_skip_admin_log
    has_import_permission = (
        import_export_admin.ImportMixin.has_import_permission
    )
    _log_actions = import_export_admin.ImportMixin._log_actions
    _create_log_entries = import_export_admin.ImportMixin._create_log_entries
    _create_log_entry = import_export_admin.ImportMixin._create_log_entry

    # Copied form related methods
    create_import_form = import_export_admin.ImportMixin.create_import_form
    get_import_form_class = import_export_admin.ImportMixin.get_import_form_class  # noqa
    get_import_form_kwargs = import_export_admin.ImportMixin.get_import_form_kwargs  # noqa
    get_import_form_initial = import_export_admin.ImportMixin.get_import_form_initial  # noqa
    create_confirm_form = import_export_admin.ImportMixin.create_confirm_form
    get_confirm_form_class = import_export_admin.ImportMixin.get_confirm_form_class  # noqa
    get_confirm_form_kwargs = import_export_admin.ImportMixin.get_confirm_form_kwargs  # noqa
    get_confirm_form_initial = import_export_admin.ImportMixin.get_confirm_form_initial  # noqa

    def get_import_context_data(self, **kwargs):
        """Get context data for import."""
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

        context = self.get_import_context_data()
        resource_classes = self.get_import_resource_classes(request)

        form = self.create_import_form(request)
        resource_kwargs = self.get_import_resource_kwargs(request)

        if request.method == "POST" and form.is_valid():
            # create ImportJob and redirect to page with it's status
            resource_class = self.choose_import_resource_class(form, request)
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
        context.update(self.admin_site.each_context(request))

        context["title"] = _("Import")
        context["form"] = form
        context["opts"] = self.model_info.meta
        context["media"] = self.media + form.media
        context["fields_list"] = self._get_fields_list_for_resources(
            resource_classes=resource_classes,
            resource_kwargs=resource_kwargs,
        )

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

        context = self.get_import_context_data()
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

        context = self.get_import_context_data()

        if request.method == "GET":
            # GET request, show parse results
            result = job.result
            context["import_job"] = job
            context["result"] = result
            context["title"] = _("Import results")

            if job.import_status == models.ImportJob.ImportStatus.PARSED:
                context["confirm_form"] = self.create_confirm_form(request)
            else:
                # display import form
                resource_classes = self.get_import_resource_classes(request)
                resource_kwargs = self.get_import_resource_kwargs(request)

                context["import_form"] = self.create_import_form(request)
                context["fields_list"] = self._get_fields_list_for_resources(
                    resource_classes=resource_classes,
                    resource_kwargs=resource_kwargs,
                )

            context.update(self.admin_site.each_context(request))
            context["opts"] = self.model_info.meta
            request.current_app = self.admin_site.name
            return TemplateResponse(
                request,
                [self.import_result_template_name],
                context,
            )

        # POST request
        if job.import_status == models.ImportJob.ImportStatus.PARSED:
            # start celery task for data importing
            job.confirm_import()
            return self._redirect_to_import_status_page(
                request=request,
                job=job,
            )

        return HttpResponseForbidden(
            "Data invalid, before importing data "
            "needs to be successfully parsed. "
            f"Current status: {job.import_status}",
        )

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
            skip_parse_step=getattr(
                settings,
                "IMPORT_EXPORT_SKIP_ADMIN_CONFIRM",
                False,
            ),
            force_import=form.cleaned_data.get("force_import", False),
        )

    def get_import_job(
        self,
        request: WSGIRequest,
        job_id: int,
    ) -> models.ImportJob:
        """Get ImportJob instance.

        Raises
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
        if job.import_status != models.ImportJob.ImportStatus.PARSED:
            return HttpResponseRedirect(redirect_to=url)

        return HttpResponseRedirect(redirect_to=url)

    def _get_fields_list_for_resources(
        self,
        resource_classes: list[type[import_export_resources.ModelResource]],
        resource_kwargs,
    ) -> list[tuple[str, list[str]]]:
        """Get fields list for resource classes."""
        resources = [
            resource_class(**resource_kwargs)
            for resource_class in resource_classes
        ]
        return [
            (
                resource.get_display_name(),
                [
                    field.column_name
                    for field in resource.get_user_visible_fields()
                ],
            )
            for resource in resources
        ]

    def changelist_view(
        self,
        request: WSGIRequest,
        context: dict[str, typing.Any] | None = None,
    ):
        """Add the check for permission to changelist template context."""
        context = context or {}
        context["has_import_permission"] = self.has_import_permission(request)
        return super().changelist_view(request, context)
