import collections
import typing
from enum import Enum

from django.db.models import QuerySet
from django.utils import timezone
from django.utils.functional import classproperty
from django.utils.translation import gettext_lazy as _

import tablib
from celery import current_task, result
from django_filters import rest_framework as filters
from django_filters.utils import translate_validation
from import_export import resources
from import_export.formats import base_formats

from .results import Error, Result, RowResult


class TaskState(Enum):
    """Class with possible task state values."""
    IMPORTING = _("Importing")
    EXPORTING = _("Exporting")
    PARSING = _("Parsing")


class CeleryResourceMixin:
    """Mixin for resources for background import/export using celery."""
    filterset_class: typing.Type[filters.FilterSet]
    SUPPORTED_FORMATS: list[
        typing.Type[base_formats.Format]
    ] = base_formats.DEFAULT_FORMATS

    def __init__(
        self,
        filter_kwargs: typing.Optional[dict[str, typing.Any]] = None,
        **kwargs,
    ):
        """Remember init kwargs."""
        self._filter_kwargs = filter_kwargs
        self.resource_init_kwargs: dict[str, typing.Any] = kwargs
        super().__init__()

    def get_queryset(self):
        """Filter export queryset via filterset class."""
        queryset = super().get_queryset()
        if not self._filter_kwargs:
            return queryset
        filter_instance = self.filterset_class(
            data=self._filter_kwargs,
        )
        if not filter_instance.is_valid():
            raise translate_validation(filter_instance.errors)
        return filter_instance.filter_queryset(queryset=queryset)

    @classproperty
    def class_path(cls) -> str:
        """Get path of class to import it."""
        return ".".join([cls.__module__, cls.__name__])

    @classmethod
    def get_supported_formats(cls) -> list[typing.Type[base_formats.Format]]:
        """Get a list of supported formats."""
        return cls.SUPPORTED_FORMATS

    @classmethod
    def get_supported_extensions_map(cls) -> dict[
        str, typing.Type[base_formats.Format],
    ]:
        """Get a map of supported formats and their extensions."""
        return {
            supported_format().get_extension(): supported_format
            for supported_format in cls.SUPPORTED_FORMATS
        }

    def import_data(
        self,
        dataset: tablib.Dataset,
        dry_run: bool = False,
        raise_errors: bool = False,
        use_transactions: typing.Optional[bool] = None,
        collect_failed_rows: bool = False,
        rollback_on_validation_errors: bool = False,
        force_import: bool = False,
        **kwargs,
    ):
        """Init task state before importing.

        If `force_import=True`, then rows with errors will be skipped.

        """
        self.initialize_task_state(
            state=(
                TaskState.IMPORTING.name if not dry_run
                else TaskState.PARSING.name
            ),
            queryset=dataset,
        )
        return super().import_data(  # type: ignore
            dataset=dataset,
            dry_run=dry_run,
            raise_errors=raise_errors,
            use_transactions=use_transactions,
            collect_failed_rows=collect_failed_rows,
            rollback_on_validation_errors=rollback_on_validation_errors,
            force_import=force_import,
            **kwargs,
        )

    def import_row(
        self,
        row,
        instance_loader,
        using_transactions=True,
        dry_run=False,
        raise_errors=False,
        force_import=False,
        **kwargs,
    ):
        """Update task status as we import rows.

        If `force_import=True`, then row errors will be stored in
        `field_skipped_errors` or `non_field_skipped_errors`.

        """
        imported_row: RowResult = super().import_row(
            row=row,
            instance_loader=instance_loader,
            using_transactions=using_transactions,
            dry_run=dry_run,
            raise_errors=raise_errors,
            **kwargs,
        )
        self.update_task_state(
            state=(
                TaskState.IMPORTING.name if not dry_run
                else TaskState.PARSING.name
            ),
        )
        if force_import and imported_row.has_error_import_type:
            imported_row = self._skip_row_with_errors(imported_row, row)
        return imported_row

    def _skip_row_with_errors(
        self,
        row_result: RowResult,
        row_data: collections.OrderedDict[str, str],
    ) -> RowResult:
        """Process row as skipped.

        Move row errors to skipped errors attributes.
        Change import type to skipped.

        """
        row_result.diff = []
        for field in self.get_fields():
            row_result.diff.append(row_data.get(field.column_name, ""))

        row_result.non_field_skipped_errors.extend(
            row_result.errors,
        )
        if row_result.validation_error is not None:
            row_result.field_skipped_errors.update(
                **row_result.validation_error.error_dict,
            )
        row_result.errors = []
        row_result.validation_error = None

        row_result.import_type = RowResult.IMPORT_TYPE_SKIP
        return row_result

    @classmethod
    def get_row_result_class(self):
        """Return custom row result class."""
        return RowResult

    @classmethod
    def get_result_class(self):
        """Geti custom result class."""
        return Result

    def export(
        self,
        queryset: QuerySet = None,
        *args,
        **kwargs,
    ) -> tablib.Dataset:
        """Init task state before exporting."""
        if queryset is None:
            queryset = self.get_queryset()
        self.initialize_task_state(
            state=TaskState.EXPORTING.name,
            queryset=queryset,
        )
        return super().export(  # type: ignore
            *args,
            **kwargs,
            queryset=queryset,
        )

    def export_resource(self, obj):
        """Update task status as we export rows."""
        resource = [
            self.export_field(field, obj) for field in self.get_export_fields()
        ]
        self.update_task_state(state=TaskState.EXPORTING.name)
        return resource

    def initialize_task_state(
        self,
        state: str,
        queryset: typing.Union[QuerySet, tablib.Dataset],
    ):
        """Set initial state of the task to track progress.

        Counts total number of instances to import/export and
        generate state for the task.

        """
        if not current_task or current_task.request.called_directly:
            return

        if isinstance(queryset, QuerySet):
            total = queryset.count()
        else:
            total = len(queryset)

        self._update_current_task_state(
            state=state,
            meta=dict(
                current=0,
                total=total,
            ),
        )

    def update_task_state(
        self,
        state: str,
    ):
        """Update state of the current event.

        Receives meta of the current task and increase the `current`
        field by 1.

        """
        if not current_task or current_task.request.called_directly:
            return

        async_result = result.AsyncResult(current_task.request.get("id"))
        if not async_result.result:
            return

        self._update_current_task_state(
            state=state,
            meta=dict(
                current=async_result.result.get("current", 0) + 1,
                total=async_result.result.get("total", 0),
            ),
        )

    def _update_current_task_state(self, state: str, meta: dict[str, int]):
        """Update state of task where resource is executed."""
        current_task.update_state(
            state=state,
            meta=meta,
        )

    def generate_export_filename(self, file_format: base_formats.Format):
        """Generate export filename."""
        return self._generate_export_filename_from_model(file_format)

    def _generate_export_filename_from_model(
        self,
        file_format: base_formats.Format,
    ):
        """Generate export file name from model name."""
        model = self._meta.model._meta.verbose_name_plural
        date_str = timezone.now().strftime("%Y-%m-%d")
        extension = file_format.get_extension()
        return f"{model}-{date_str}.{extension}"

    @classmethod
    def get_error_result_class(cls):
        """Override default error class."""
        return Error


class CeleryResource(CeleryResourceMixin, resources.Resource):
    """Resource which supports importing via celery."""


class CeleryModelResource(CeleryResourceMixin, resources.ModelResource):
    """ModelResource which supports importing via celery."""

    @classmethod
    def get_model_queryset(cls):
        """Return a queryset of all objects for this model.

        Override this if you
        want to limit the returned queryset.

        Same as resources.ModelResource get_queryset.

        """
        return cls._meta.model.objects.all()
