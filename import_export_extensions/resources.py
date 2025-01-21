import collections
import enum
import functools
import typing

from django.conf import settings
from django.core.exceptions import FieldError, ValidationError
from django.db.models import QuerySet
from django.utils import timezone
from django.utils.functional import classproperty
from django.utils.translation import gettext_lazy as _

import tablib
from celery import current_task
from django_filters import rest_framework as filters
from django_filters.utils import translate_validation
from import_export import fields, resources
from import_export.formats import base_formats

from .results import Error, Result, RowResult


class TaskState(enum.Enum):
    """Class with possible task state values."""

    IMPORTING = _("Importing")
    EXPORTING = _("Exporting")
    PARSING = _("Parsing")


class CeleryResourceMixin:
    """Mixin for resources for background import/export using celery."""

    filterset_class: type[filters.FilterSet]
    SUPPORTED_FORMATS: list[type[base_formats.Format]] = (
        base_formats.DEFAULT_FORMATS
    )

    def __init__(
        self,
        filter_kwargs: dict[str, typing.Any] | None = None,
        ordering: collections.abc.Sequence[str] | None = None,
        created_by: typing.Any | None = None,
        **kwargs,
    ):
        """Remember init kwargs."""
        self._filter_kwargs = filter_kwargs
        self._ordering = ordering
        self._created_by = created_by
        self.resource_init_kwargs: dict[str, typing.Any] = kwargs
        self.total_objects_count = 0
        self.current_object_number = 0
        super().__init__()

    @functools.cached_property
    def status_update_row_count(self):
        """Rows count after which to update celery task status."""
        return getattr(
            self._meta,
            "status_update_row_count",
            settings.STATUS_UPDATE_ROW_COUNT,
        )

    @classmethod
    def get_model_queryset(cls) -> QuerySet:
        """Return a queryset of all objects for this model.

        Override this if you
        want to limit the returned queryset.

        Same as resources.ModelResource get_queryset.

        """
        return cls._meta.model.objects.all()

    def get_queryset(self):
        """Filter export queryset via filterset class."""
        queryset = self.get_model_queryset()
        try:
            queryset = queryset.order_by(*(self._ordering or ()))
        except FieldError as error:
            raise ValidationError(
                {
                    # Split error text not to expose all fields to api clients.
                    "ordering": str(error).split("Choices are:")[0].strip(),
                },
            ) from error
        if not self._filter_kwargs:
            return queryset
        filter_instance = self.filterset_class(
            data=self._filter_kwargs,
        )
        if not filter_instance.is_valid():
            raise translate_validation(filter_instance.errors)
        return filter_instance.filter_queryset(queryset=queryset)

    @classproperty
    def class_path(self) -> str:
        """Get path of class to import it."""
        return f"{self.__module__}.{self.__name__}"

    @classmethod
    def get_supported_formats(cls) -> list[type[base_formats.Format]]:
        """Get a list of supported formats."""
        return cls.SUPPORTED_FORMATS

    @classmethod
    def get_supported_extensions_map(
        cls,
    ) -> dict[
        str,
        type[base_formats.Format],
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
        use_transactions: bool | None = None,
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
                TaskState.IMPORTING.name
                if not dry_run
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
                TaskState.IMPORTING.name
                if not dry_run
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
        for field in self.fields.values():
            row_result.diff.append(row_data.get(field.column_name, ""))

        row_result.non_field_skipped_errors.extend(
            row_result.errors,
        )
        if row_result.validation_error is not None:
            row_result.field_skipped_errors.update(
                **row_result.validation_error.update_error_dict({}),
            )
        row_result.errors = []
        row_result.validation_error = None

        row_result.import_type = RowResult.IMPORT_TYPE_SKIP
        return row_result

    @classmethod
    def get_row_result_class(cls) -> type[RowResult]:
        """Return custom row result class."""
        return RowResult

    @classmethod
    def get_result_class(cls) -> type[Result]:
        """Get custom result class."""
        return Result

    def export(
        self,
        queryset: QuerySet | None = None,
        **kwargs,
    ) -> tablib.Dataset:
        """Init task state before exporting."""
        if queryset is None:
            queryset = self.get_queryset()

        # Necessary for correct calculation of the total, this method is called
        # later inside parent resource class
        queryset = self.filter_export(queryset, **kwargs)

        self.initialize_task_state(
            state=TaskState.EXPORTING.name,
            queryset=queryset,
        )
        return super().export(  # type: ignore
            queryset=queryset,
            **kwargs,
        )

    def export_resource(
        self,
        obj,
        selected_fields: list[fields.Field] | None = None,
        **kwargs,
    ):
        """Update task status as we export rows."""
        resource = super().export_resource(obj, selected_fields, **kwargs)  # type: ignore
        self.update_task_state(state=TaskState.EXPORTING.name)
        return resource

    def initialize_task_state(
        self,
        state: str,
        queryset: QuerySet | tablib.Dataset,
    ):
        """Set initial state of the task to track progress.

        Counts total number of instances to import/export and
        generate state for the task.

        """
        if not current_task or current_task.request.called_directly:
            return

        self.total_objects_count = (
            queryset.count()
            if isinstance(queryset, QuerySet)
            else len(queryset)
        )

        self._update_current_task_state(
            state=state,
            meta={
                "current": self.current_object_number,
                "total": self.total_objects_count,
            },
        )

    def update_task_state(
        self,
        state: str,
    ):
        """Update state of the current event.

        Receives meta of the current task and increase the `current`. Task
        state is updated when current item is a multiple of
        `self.status_update_row_count` or equal to total number of items.

        For example: once every 1000 objects (if the current object is 1000,
        2000, 3000) or when current object is the last object, in order to
        complete the import/export.

        This needed to increase the speed of import/export by reducing number
        of task status updates.

        """
        if not current_task or current_task.request.called_directly:
            return

        self.current_object_number += 1

        is_reached_update_count = (
            self.current_object_number % self.status_update_row_count == 0
        )
        is_last_object = self.current_object_number == self.total_objects_count

        if is_reached_update_count or is_last_object:
            self._update_current_task_state(
                state=state,
                meta={
                    "current": self.current_object_number,
                    "total": self.total_objects_count,
                },
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
    def get_error_result_class(cls) -> type[Error]:
        """Override default error class."""
        return Error


class CeleryResource(CeleryResourceMixin, resources.Resource):
    """Resource which supports importing via celery."""


class CeleryModelResource(CeleryResourceMixin, resources.ModelResource):
    """ModelResource which supports importing via celery."""

    class Meta:
        store_instance = True
