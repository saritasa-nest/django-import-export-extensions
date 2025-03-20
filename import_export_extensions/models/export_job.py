import pathlib
import traceback
import typing
import uuid

from django.core import files as django_files
from django.db import models, transaction
from django.utils import encoding, module_loading, timezone
from django.utils.translation import gettext_lazy as _

from celery import current_app, result, states
from import_export.formats import base_formats

from .. import signals
from . import tools
from .core import BaseJob, TaskStateInfo


class ExportJob(BaseJob):
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

    file_format_path = models.CharField(
        max_length=128,
        verbose_name=_("Export path to class"),
        help_text=_(
            "Export file format as path to base_formats class",
        ),
    )

    data_file = models.FileField(
        max_length=512,
        storage=tools.select_storage,
        verbose_name=_("Data file"),
        upload_to=tools.upload_export_file_to,
        help_text=_("File that contain exported data"),
    )

    export_task_id = models.CharField(  # noqa: DJ001
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

    class Meta:
        verbose_name = _("Export job")
        verbose_name_plural = _("Export jobs")

    def __str__(self) -> str:
        """Return string representation."""
        resource_name = pathlib.Path(self.resource_path).suffix.lstrip(".")
        file_format = pathlib.Path(self.file_format_path).suffix.lstrip(".")

        return f"ExportJob(resource={resource_name}, {file_format=})"

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
    def progress(self) -> TaskStateInfo | None:
        """Return dict with export state."""
        if (
            self.export_task_id
            and self.export_status == self.ExportStatus.EXPORTING
        ):
            return self._get_task_state(self.export_task_id)

        return None

    def _check_export_status_correctness(
        self,
        expected_statuses: typing.Sequence[ExportStatus],
    ) -> None:
        """Raise `ValueError` if `ExportJob` is in incorrect state."""
        if self.export_status not in expected_statuses:
            raise ValueError(
                f"ExportJob with id {self.id} has incorrect status: "
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
            self._handle_error(
                error_message=str(error),
                traceback=traceback.format_exc(),
                exception=error,
            )

    def cancel_export(self) -> None:
        """Cancel current data export.

        ExportJob can be CANCELLED only from following states:
            - CREATED
            - EXPORTING

        """
        self._check_export_status_correctness(
            expected_statuses=(  # type: ignore
                self.ExportStatus.CREATED,
                self.ExportStatus.EXPORTING,
            ),
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
        export_data = self.file_format.export_data(dataset=self.result)
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

        self._handle_error(
            error_message=str(async_result.info),
            traceback=str(async_result.traceback),
        )
        return dict(
            state=async_result.state,
            info={},
        )

    def _handle_error(
        self,
        error_message: str,
        traceback: str,
        exception: Exception | None = None,
    ):
        """Update job's status in case of error."""
        self.export_status = self.ExportStatus.EXPORT_ERROR
        error_message_limit = self._meta.get_field("error_message").max_length
        self.error_message = error_message[:error_message_limit]
        self.traceback = traceback
        self.save(
            update_fields=[
                "error_message",
                "traceback",
                "export_status",
            ],
        )
        signals.export_job_failed.send(
            sender=self.__class__,
            instance=self,
            error_message=self.error_message,
            traceback=self.traceback,
            exception=exception,
        )
