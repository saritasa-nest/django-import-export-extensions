import typing

from django.core.cache import cache
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

from ... import forms, models
from .base import FormatType, ModelInfo, ResourceObj, ResourceType


class CeleryImportAdminMixin:
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

    # Resource class
    resource_class: ResourceType = None     # type: ignore
    # Import data encoding
    from_encoding: str = "utf-8"

    change_list_template: str = "admin/change_list/change_list_import.html"

    # Statuses that should be displayed on 'results' page
    results_statuses = models.ImportJob.results_statuses

    # Template used to display ImportForm
    celery_import_template: str = "admin/celery_import.html"

    # Template used to display status of import jobs
    import_status_template: str = "admin/celery_import_status.html"

    # template used to display results of import jobs
    import_result_template_name: str = "admin/celery_import_results.html"

    @property
    def model_info(self) -> ModelInfo:
        """Get info of imported model."""
        return ModelInfo(
            meta=self.model._meta,
        )

    def get_import_resource_kwargs(
        self,
        request: WSGIRequest,
        *args,
        **kwargs,
    ) -> dict[str, typing.Any]:
        """Get kwargs for import resource."""
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

    def get_import_resource(
        self,
        request: WSGIRequest,
        *args,
        **kwargs,
    ) -> ResourceObj:
        """Get initialized resource."""
        return self.get_import_resource_class()(
            **self.get_import_resource_kwargs(
                request,
                *args,
                **kwargs,
            ),
        )

    def get_import_resource_class(self) -> ResourceType:
        """Return ResourceClass to use for import."""
        return self.get_resource_class()

    def get_import_formats(self) -> list[FormatType]:
        """Get supported import formats."""
        return [
            import_format for import_format in
            self.get_resource_class().get_supported_formats()
            if import_format().can_import()
        ]

    def get_import_format_by_ext(
        self,
        extension: str,
    ) -> typing.Union[FormatType, None]:
        """Return available import formats."""
        for import_format in self.get_import_formats():
            if import_format().get_title().upper() == extension.upper():
                return import_format
        return None

    def get_context_data(
        self,
        request: WSGIRequest,
        **kwargs,
    ) -> dict[str, typing.Any]:
        """Get context data."""
        return {}

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
                name=f"{self.model_info.app_model_name}_celery_import",
            ),
            re_path(
                r"^celery-import/(?P<job_id>\d+)/$",
                self.admin_site.admin_view(self.celery_import_job_status_view),
                name=(
                    f"{self.model_info.app_model_name}"
                    f"_celery_import_job_status"
                ),
            ),
            re_path(
                r"^celery-import/(?P<job_id>\d+)/results/$",
                self.admin_site.admin_view(
                    self.celery_import_job_results_view,
                ),
                name=(
                    f"{self.model_info.app_model_name}"
                    f"_celery_import_job_results"
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
        resource = self.get_import_resource(request, *args, **kwargs)
        context = self.get_context_data(request)

        form = forms.ImportForm(
            request.POST or None,
            request.FILES or None,
        )

        if request.method == "POST" and form.is_valid():
            # create ImportJob and redirect to page with it's status
            job = self.create_import_job(
                request=request,
                resource=resource,
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
        context["fields"] = [
            f.column_name for f in resource.get_user_visible_fields()
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

        """
        job = self.get_job(request, job_id)
        if job.import_status in self.results_statuses:
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
        job = self.get_job(request=request, job_id=job_id)
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
                context["import_form"] = forms.ImportForm()
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
        resource: ResourceObj,
    ):
        """Create and return instance of import job."""
        return models.ImportJob.objects.create(
            resource_path=resource.class_path,
            data_file=form.cleaned_data["import_file"],
            resource_kwargs=resource.resource_init_kwargs,
            created_by=request.user,
        )

    def get_job(
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
            f"admin:{self.model_info.app_model_name}_celery_import_job_status"
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
            f"admin:{self.model_info.app_model_name}_celery_import_job_results"
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
