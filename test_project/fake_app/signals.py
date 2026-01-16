import logging

from django import dispatch

from import_export_extensions.models.core import BaseJob
from import_export_extensions.signals import (
    export_job_failed,
    import_job_failed,
)


@dispatch.receiver(export_job_failed)
@dispatch.receiver(import_job_failed)
def job_error_hook(
    sender: type[BaseJob],
    instance: BaseJob,
    error_message: str,
    traceback: str,
    exception: Exception | None,
    **kwargs,
) -> None:
    """Present an example of job error hook."""
    logging.getLogger(__file__).warning(f"{instance}, {error_message}")
