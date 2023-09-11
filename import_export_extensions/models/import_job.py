import os
import pathlib
import traceback
import uuid
from typing import Optional, Sequence, Type

from django.conf import settings
from django.db import models, transaction
from django.utils import encoding, module_loading, timezone
from django.utils.translation import gettext_lazy as _

import tablib
from celery import current_app, result, states
from import_export.formats import base_formats
from import_export.results import Result
from picklefield.fields import PickledObjectField

from . import tools
from .core import TaskStateInfo, TimeStampedModel


class ImportJob(TimeStampedModel):
    """Abstract model for managing celery import jobs.

    Encapsulate all logic related to celery import.

    Import steps:

    1. Create ``ImportJob`` with resource initialization parameters and file
        with data to be imported from
    2. Dry run. Try to import all data from file and collect statistics (
        errors, new rows, updated rows).
    3. If data for import is correct - import data from file to database.

    """

    class ImportStatus(models.TextChoices):
        """ImportJob possible statuses.

        * CREATED:
            import job is just created, no parsing done
        * PARSING:
            parse job started
        * PARSED:
            data_file parsed, no errors in data occurred
        * INPUT_ERROR:
            data_file parsed, data contain errors
        * PARSE_ERROR:
            data_file can't be parsed (invalid format, etc.)
        * IMPORT_CONFIRMED
            import confirmed but not started yet
        * IMPORTING:
            importing job started
        * IMPORTED:
            data from data_file imported to DB w/o errors
        * IMPORT_ERROR:
            unknown error during import
        * CANCELLED:
            import job has been cancelled (revoked)

        State diagrams::

            CREATED
               |
            .parse_data()
               |
            PARSING  - (INPUT_ERROR, PARSE_ERROR)
               |
            PARSED
               |
            .confirm_import()
               |
            IMPORT_CONFIRMED
               |
            .import_data()
               |
            IMPORTING - IMPORT_ERROR
               |
            IMPORTED

        """

        CREATED = "CREATED", _("Created")
        PARSING = "PARSING", _("Parsing")
        PARSED = "PARSED", _("Parsed")
        INPUT_ERROR = "INPUT_ERROR", _("Input data error")
        PARSE_ERROR = "PARSE_ERROR", _("Parse error")
        CONFIRMED = "CONFIRMED", _("Import confirmed")
        IMPORTING = "IMPORTING", _("Importing")
        IMPORTED = "IMPORTED", _("Imported")
        IMPORT_ERROR = "IMPORT_ERROR", _("Import error")
        CANCELLED = "CANCELLED", _("Cancelled")

    results_statuses = (
        ImportStatus.PARSED,
        ImportStatus.INPUT_ERROR,
        ImportStatus.IMPORTED,
        ImportStatus.IMPORT_ERROR,
    )

    progress_statuses = (
        ImportStatus.PARSING,
        ImportStatus.IMPORTING,
    )

    parse_finished_statuses = (
        ImportStatus.INPUT_ERROR,
        ImportStatus.PARSE_ERROR,
        ImportStatus.PARSED,
    )

    import_finished_statuses = (
        ImportStatus.IMPORTED,
        ImportStatus.IMPORT_ERROR,
    )

    success_statuses = (
        ImportStatus.IMPORTED,
        ImportStatus.PARSED,
    )

    failure_statuses = (
        ImportStatus.INPUT_ERROR,
        ImportStatus.PARSE_ERROR,
    )

    import_status = models.CharField(
        max_length=20,
        choices=ImportStatus.choices,
        default=ImportStatus.CREATED,
        verbose_name=_("Job status"),
    )

    resource_path = models.CharField(
        max_length=128,
        verbose_name=_("Resource class path"),
        help_text=_(
            "Dotted path to subclass of `import_export.Resource` that "
            "should be used for import",
        ),
    )

    data_file = models.FileField(
        max_length=512,
        verbose_name=_("Data file"),
        upload_to=tools.upload_import_file_to,
        help_text=_("File that contain data to be imported"),
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
        help_text=_("Python traceback in case of parse/import error"),
    )
    error_message = models.CharField(
        max_length=128,
        blank=True,
        default=str,
        verbose_name=_("Error message"),
        help_text=_("Python error message in case of parse/import error"),
    )

    result = PickledObjectField(
        default=str,
        verbose_name=_("Import result"),
        help_text=_(
            "Internal import result object that contain "
            "info about import statistics. Pickled Python object",
        ),
    )

    parse_task_id = models.CharField(
        default=str,
        max_length=36,
        verbose_name=_("Parsing task ID"),
        help_text=_("Celery task ID that start `parse_data`"),
    )

    import_task_id = models.CharField(
        max_length=36,
        default=str,
        verbose_name=_("Import task ID"),
        help_text=_("Celery task ID that start `import_data`"),
    )

    parse_finished = models.DateTimeField(
        editable=False,
        null=True,
        verbose_name=_("Parse finished"),
    )

    import_started = models.DateTimeField(
        editable=False,
        null=True,
        verbose_name=_("Import started"),
    )

    import_finished = models.DateTimeField(
        editable=False,
        null=True,
        verbose_name=_("Import finished"),
    )

    created_by = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        editable=False,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Created by"),
        help_text=_("User which started import"),
    )

    skip_parse_step = models.BooleanField(
        default=False,
        help_text=_("Start importing without confirmation"),
        verbose_name=_("Skip parse step"),
    )

    class Meta:
        verbose_name = _("Import job")
        verbose_name_plural = _("Import jobs")

    def __str__(self) -> str:
        """Return string representation."""
        resource_name = pathlib.Path(self.resource_path).suffix.lstrip(".")

        return f"ImportJob(resource={resource_name})"

    def save(
        self,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,
    ):
        """Start task for data parsing when ImportJob is created.

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
        if not is_created:
            return

        if self.skip_parse_step:
            self.import_task_id = str(uuid.uuid4())
            self.import_started = timezone.now()
            self.save(
                update_fields=[
                    "import_task_id",
                    "import_started",
                ],
            )
            transaction.on_commit(self._start_import_data_task)
        else:
            self.parse_task_id = str(uuid.uuid4())
            self.save(update_fields=["parse_task_id"])
            transaction.on_commit(self.start_parse_data_task)

    @property
    def resource(self):
        """Get initialized resource instance."""
        resource_class = module_loading.import_string(self.resource_path)
        resource = resource_class(
            **self.resource_kwargs,
        )
        return resource

    @property
    def progress(self) -> Optional[TaskStateInfo]:
        """Return dict with parsing state.

        Example for sync mode::

            {
                'state': 'PARSING',
                'info': None
            }

        Example for background (celery) mode::

            {
                'state': 'PARSING',
                'info': {'current': 15, 'total': 100}
            }

        Possible states:
            1. PENDING
            2. STARTED
            3. SUCCESS
            4. PARSING - custom status that also set importing info

        https://docs.celeryproject.org/en/latest/userguide/tasks.html#states

        """
        if self.import_status not in (
            self.ImportStatus.PARSING,
            self.ImportStatus.IMPORTING,
        ):
            return None

        current_task = (
            self.parse_task_id
            if self.import_status == self.ImportStatus.PARSING
            else self.import_task_id
        )

        if not current_task or current_app.conf.task_always_eager:
            return dict(
                state=self.import_status.upper(),
                info=None,
            )

        return self._get_task_state(current_task)

    def _check_import_status_correctness(
        self,
        expected_statuses: Sequence[ImportStatus],
    ) -> None:
        """Raise `ValueError` if `ImportJob` is in incorrect state."""
        if self.import_status not in expected_statuses:
            raise ValueError(
                f"ImportJob with id {self.id} has incorrect status: "
                f"`{self.import_status}`. Expected statuses:"
                f" {[status.value for status in expected_statuses]}",
            )

    def start_parse_data_task(self):
        """Start parsing task."""
        from .. import tasks

        tasks.parse_data_task.apply_async(
            kwargs=dict(job_id=self.pk),
            task_id=self.parse_task_id,
        )

    def parse_data(self):
        """Parse `data_file` and collect results.

        Sets `result` and/or `traceback` and update `status`.

        """
        self._check_import_status_correctness(
            expected_statuses=(self.ImportStatus.CREATED,),
        )

        self.import_status = self.ImportStatus.PARSING
        self.save(update_fields=["import_status"])

        try:
            self.result = self._parse_data_inner()
            self.import_status = (
                self.ImportStatus.INPUT_ERROR
                if self.result.has_errors()
                or self.result.has_validation_errors()
                else self.ImportStatus.PARSED
            )
            self.parse_finished = timezone.now()
            self.save(
                update_fields=[
                    "import_status",
                    "result",
                    "parse_finished",
                ],
            )
        except Exception as error:
            self.traceback = traceback.format_exc()
            self.error_message = str(error)[:128]
            self.import_status = self.ImportStatus.PARSE_ERROR
            self.save(
                update_fields=[
                    "traceback",
                    "error_message",
                    "import_status",
                ],
            )

    def _parse_data_inner(self) -> Result:
        """Run import process with `dry_run == True`.

        Returns:
            apps.utils.async_import_export.results.Result instance with
            parsing results

        """
        dataset = self._get_data_to_import()
        return self.resource.import_data(
            dataset,
            dry_run=True,
            raise_errors=False,
            collect_failures=True,
        )

    def confirm_import(self):
        """Update task status to IMPORT_CONFIRMED and start parsing.

        This is "intermediate" state between PARSED and IMPORTING and required
        because of possible latency of celery task start.

        Celery task is manually called with `apply_async`, to provide
        possibility of custom `task_id` with which task will be run.

        """
        self._check_import_status_correctness(
            expected_statuses=(self.ImportStatus.PARSED,),
        )

        self.import_status = self.ImportStatus.CONFIRMED
        self.import_task_id = str(uuid.uuid4())
        self.import_started = timezone.now()
        self.save(
            update_fields=[
                "import_status",
                "import_started",
                "import_task_id",
            ],
        )
        transaction.on_commit(self._start_import_data_task)

    def _start_import_data_task(self):
        """Start import task."""
        from .. import tasks

        tasks.import_data_task.apply_async(
            kwargs=dict(job_id=self.pk),
            task_id=self.import_task_id,
        )

    def import_data(self):
        """Import data from `data_file` to DB."""
        expected_status = (
            self.ImportStatus.CREATED
            if self.skip_parse_step
            else self.ImportStatus.CONFIRMED
        )
        self._check_import_status_correctness(
            expected_statuses=(expected_status,),
        )

        self.import_status = self.ImportStatus.IMPORTING
        self.save(update_fields=["import_status"])
        try:
            self.result = self._import_data_inner()
            self.import_status = self.ImportStatus.IMPORTED
            self.import_finished = timezone.now()
            self.save(
                update_fields=[
                    "import_status",
                    "result",
                    "import_finished",
                ],
            )
        except Exception as error:
            self.traceback = traceback.format_exc()
            self.error_message = str(error)[:128]
            self.import_status = self.ImportStatus.IMPORT_ERROR
            self.save(
                update_fields=[
                    "import_status",
                    "error_message",
                    "traceback",
                ],
            )

    def _import_data_inner(self) -> Result:
        """Run import process with saving to DB.

        Transaction is not used as import is slow, so before it finish -
        no instances are saved to DB. So sync works incorrect

        Returns:
            import_export.results.Result instance with parsing results

        """
        data_to_import = self._get_data_to_import()
        return self.resource.import_data(
            data_to_import,
            dry_run=False,
            raise_errors=True,
            use_transactions=True,
            collect_failures=True,
        )

    def _get_import_format_by_ext(
        self,
        file_ext: str,
    ) -> Type[base_formats.Format]:
        """Determine import file format by file extension."""
        supported_formats = self.resource.get_supported_formats()
        for import_format in supported_formats:
            if import_format().get_title().upper() == file_ext.upper().replace(
                ".", "",
            ):
                return import_format
        supported_formats_titles = ",".join(
            supported_format().get_title()
            for supported_format in supported_formats
        )
        raise ValueError(
            f"Incorrect import format: {file_ext}. "
            f"Supported formats: {supported_formats_titles}",
        )

    def _get_data_to_import(self) -> tablib.Dataset:
        """Read ``self.data_file`` content and convert it to dataset."""
        _, file_ext = os.path.splitext(self.data_file.name)
        input_format = self._get_import_format_by_ext(
            file_ext=file_ext,
        )()
        data = self.data_file.read()
        self.data_file.seek(0)
        if not input_format.is_binary():
            data = encoding.force_str(data)
        data_to_import = input_format.create_dataset(data)
        num_rows = len(data_to_import)
        if num_rows > settings.IMPORT_EXPORT_MAX_DATASET_ROWS:
            raise ValueError(
                f"Too many rows `{num_rows}`"
                f"(Max: {settings.IMPORT_EXPORT_MAX_DATASET_ROWS}). "
                f"Input file may be broken. "
                f"If it's spreadsheet file, please delete empty rows.",
            )
        return data_to_import

    def cancel_import(self) -> None:
        """Cancel current data import.

        ImportJob can be CANCELLED only from following states:
            - CREATED
            - PARSING
            - CONFIRMED
            - IMPORTING

        """
        status_task_field_map = {
            self.ImportStatus.CREATED: "parse_task_id",
            self.ImportStatus.PARSING: "parse_task_id",
            self.ImportStatus.CONFIRMED: "import_task_id",
            self.ImportStatus.IMPORTING: "import_task_id",
        }
        self._check_import_status_correctness(
            expected_statuses=status_task_field_map.keys(),  # type: ignore
        )

        # send signal to celery to revoke task
        task_id = getattr(self, status_task_field_map[self.import_status])
        current_app.control.revoke(task_id, terminate=True)

        self.import_status = self.ImportStatus.CANCELLED
        self.save(update_fields=["import_status"])

    def _get_task_state(self, task_id: str) -> TaskStateInfo:
        """Get state info for passed task_id.

        This method may change job status if task failed, but we did not
        save info about this to DB.

        This may happen if task start import/parsing, but processes was killed.
        In that case, job have status `importing`, but it can't be finished.

        """
        async_result = result.AsyncResult(task_id)
        if async_result.state in states.EXCEPTION_STATES:
            # update job's status
            self.import_status = (
                self.ImportStatus.PARSE_ERROR
                if self.import_status == self.ImportStatus.PARSING
                else self.ImportStatus.IMPORT_ERROR
            )
            self.error_message = str(async_result.info)[:128]
            self.traceback = str(async_result.traceback)
            self.save(
                update_fields=[
                    "error_message",
                    "traceback",
                    "import_status",
                ],
            )
            return dict(
                state=async_result.state,
                info={},
            )
        return dict(
            state=async_result.state,
            info=async_result.info,
        )
