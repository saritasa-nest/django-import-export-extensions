import pathlib
import traceback
import typing
import uuid

from django.conf import settings
from django.core import files as django_files
from django.db import models, transaction
from django.utils import encoding, module_loading, timezone
from django.utils.translation import gettext_lazy as _

from celery import current_app, result, states
from import_export.formats import base_formats
from picklefield import PickledObjectField

from . import tools
from .core import TaskStateInfo, TimeStampedModel


class ExportJob(TimeStampedModel):
    """Abstract model for managing celery export jobs.

    Encapsulate all logic related to celery export.

    Export steps:

    1. Create ExportJob with resource initialization parameters.
    2. Try to export all data to file.
    3. If everything correct - export data to file from database.

    Export file saves in media files.

    """

    class ExportStatus(models.TextChoices):
        """ExportJob possible statuses.

        * CREATED:
            export job is just created, no exporting done
        * EXPORTING:
            export job started
        * EXPORT_ERROR:
            DB queryset not exported, errors
        * EXPORTED:
            DB queryset exported, no errors occurred

        State diagrams::

            CREATED
               |
            EXPORTING  - (EXPORT_ERROR)
               |
            EXPORTED

        """

        CREATED = "CREATED", _("Created")
        EXPORTING = "EXPORTING", _("Exporting")
        EXPORT_ERROR = "EXPORT_ERROR", _("Export Error")
        EXPORTED = "EXPORTED", _("Exported")
        CANCELLED = "CANCELLED", _("Cancelled")

    export_finished_statuses = (
        ExportStatus.EXPORTED,
        ExportStatus.EXPORT_ERROR,
    )

    export_status = models.CharField(
        max_length=20,
        choices=ExportStatus.choices,
        default=ExportStatus.CREATED,
        verbose_name=_("Job status"),
    )

    resource_path = models.CharField(
        max_length=128,
        verbose_name=_("Resource class path"),
        help_text=_(
            "Dotted path to subclass of `import_export.Resource` that "
            "should be used for export",
        ),
    )

    file_format_path = models.CharField(
        max_length=128,
        verbose_name=_("Export path to class"),
        help_text=_(
            "Export file format as path to base_formats class",
        ),
    )

    data_file = models.FileField(
        max_length=512,
        verbose_name=_("Data file"),
        upload_to=tools.upload_export_file_to,
        help_text=_("File that contain exported data"),
    )

    resource_kwargs = models.JSONField(
        default=dict,
        verbose_name=_("Resource kwargs"),
        help_text=_("Keyword parameters required for resource initialization"),
    )

    traceback = models.TextField(
        blank=True,
        default=str,
        verbose_name=_("Traceback"),
        help_text=_("Python traceback in case of export error"),
    )
    error_message = models.CharField(
        max_length=128,
        blank=True,
        default=str,
        verbose_name=_("Error message"),
        help_text=_("Python error message in case of export error"),
    )

    result = PickledObjectField(
        default=str,
        verbose_name=_("Export result"),
        help_text=_(
            "Internal export result object that contain "
            "info about export statistics. Pickled Python object",
        ),
    )

    export_task_id = models.CharField(  # noqa: DJ01
        verbose_name=_("Export task ID"),
        max_length=36,
        null=True,
        blank=True,
        help_text=_("Celery task ID that start `export_data`"),
    )

    export_started = models.DateTimeField(
        verbose_name=_("Export started"),
        editable=False,
        blank=True,
        null=True,
    )

    export_finished = models.DateTimeField(
        verbose_name=_("Export finished"),
        editable=False,
        blank=True,
        null=True,
    )

    created_by = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        editable=False,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Created by"),
        help_text=_("User which started export"),
    )

    class Meta:
        verbose_name = _("Export job")
        verbose_name_plural = _("Export jobs")

    def __str__(self) -> str:
        """Return string representation."""
        resource_name = pathlib.Path(self.resource_path).suffix.lstrip(".")
        file_format = pathlib.Path(self.file_format_path).suffix.lstrip(".")

        return f"ExportJob(resource={resource_name}, file_format={file_format})"

    def save(
        self,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,
    ):
        """Start task for data exporting when ExportJob is created.

        Celery task is manually called with `apply_async`, to provide
        possibility of custom `task_id` with which task will be run.

        """
        is_created = self._state.adding
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )
        if is_created:
            self.export_task_id = str(uuid.uuid4())
            self.save(update_fields=["export_task_id"])
            transaction.on_commit(self._start_export_data_task)

    @property
    def resource(self):
        """Get initialized resource instance."""
        resource_class = module_loading.import_string(self.resource_path)
        resource = resource_class(
            created_by=self.created_by,
            **self.resource_kwargs,
        )
        return resource

    @property
    def file_format(self) -> base_formats.Format:
        """Get initialized format instance."""
        return module_loading.import_string(self.file_format_path)()

    @property
    def export_filename(self) -> str:
        """Get filename for export result file."""
        return self.resource.generate_export_filename(
            file_format=self.file_format,
        ).replace("/", "-")

    @property
    def progress(self) -> typing.Optional[TaskStateInfo]:
        """Return dict with parsing state.

        Example for sync mode::

            {
                'state': 'EXPORTING',
                'info': None
            }

        Example for celery (celery) mode::

            {
                'state': 'EXPORTING',
                'info': {'current': 15, 'total': 100}
            }

        Possible states:
            1. PENDING
            2. STARTED
            3. SUCCESS
            4. EXPORTING - custom status that also set export info

        https://docs.celeryproject.org/en/latest/userguide/tasks.html#states

        """
        if self.export_status not in (self.ExportStatus.EXPORTING,):
            return None

        if not self.export_task_id or current_app.conf.task_always_eager:
            return dict(
                state=self.export_status.upper(),
                info=None,
            )

        return self._get_task_state(self.export_task_id)

    def _check_import_status_correctness(
        self,
        expected_statuses: typing.Sequence[ExportStatus],
    ) -> None:
        """Raise `ValueError` if `ImportJob` is in incorrect state."""
        if self.export_status not in expected_statuses:
            raise ValueError(
                f"ImportJob with id {self.id} has incorrect status: "
                f"`{self.export_status}`. Expected statuses:"
                f" {[status.value for status in expected_statuses]}",
            )

    def _start_export_data_task(self):
        """Start export data task."""
        from .. import tasks

        tasks.export_data_task.apply_async(
            kwargs=dict(job_id=self.pk),
            task_id=self.export_task_id,
        )

    def export_data(self):
        """Export data to `data_file` from DB."""
        self.export_status = self.ExportStatus.EXPORTING
        self.export_started = timezone.now()
        self.save(
            update_fields=[
                "export_status",
                "export_started",
            ],
        )
        try:
            self._export_data_inner()
            self.export_status = self.ExportStatus.EXPORTED
            self.export_finished = timezone.now()
            self.save(
                update_fields=[
                    "export_status",
                    "export_finished",
                ],
            )
        except Exception as error:
            self.traceback = traceback.format_exc()
            self.error_message = str(error)[:512]
            self.export_status = self.ExportStatus.EXPORT_ERROR
            self.save(
                update_fields=[
                    "export_status",
                    "traceback",
                    "error_message",
                ],
            )

    def cancel_export(self) -> None:
        """Cancel current data export.

        ExportJob can be CANCELLED only from following states:
            - CREATED
            - EXPORTING

        """
        self._check_import_status_correctness(
            expected_statuses=[
                self.ExportStatus.CREATED.value,
                self.ExportStatus.EXPORTING.value,
            ],
        )

        # send signal to celery to revoke task
        current_app.control.revoke(self.export_task_id, terminate=True)

        self.export_status = self.ExportStatus.CANCELLED
        self.save(update_fields=["export_status"])

    def _export_data_inner(self):
        """Run export process with saving to file."""
        self.result = self.resource.export()
        self.save(update_fields=["result"])

        # `export_data` may be bytes (base formats such as xlsx, csv, etc.) or
        # file object (formats inherited from `BaseZipExport`)
        export_data = self.file_format.export_data(
            dataset=self.result,
            escape_html=self.resource_kwargs.get("escape_html", False),
            escape_formulae=self.resource_kwargs.get("escape_formulae", False),
        )
        # create file if `export_data` is not file
        if not hasattr(export_data, "read"):
            export_data = django_files.base.ContentFile(
                content=encoding.force_bytes(export_data),
            )
        self.data_file.save(
            name=self.export_filename,
            content=export_data,
            save=True,
        )

    def _get_task_state(self, task_id: str) -> TaskStateInfo:
        """Get state info for passed task_id.

        This method may change job status if task failed, but we did not
        save info about this to DB.

        This may happen if task start exporting, but processes was killed.
        In that case, job have status `importing`, but it can't be finished.

        """
        async_result = result.AsyncResult(task_id)
        if async_result.state not in states.EXCEPTION_STATES:
            return dict(
                state=async_result.state,
                info=async_result.info,
            )

        # Update job's status in case of exception
        self.export_status = ExportJob.ExportStatus.EXPORT_ERROR
        self.error_message = str(async_result.info)[:128]
        self.traceback = str(async_result.traceback)
        self.save(
            update_fields=[
                "error_message",
                "traceback",
                "export_status",
            ],
        )
        return dict(
            state=async_result.state,
            info={},
        )
