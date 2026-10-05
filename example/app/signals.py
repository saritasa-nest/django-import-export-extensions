import logging

from django import dispatch

from import_export_extensions import models, signals


@dispatch.receiver(signals.export_job_failed)
@dispatch.receiver(signals.import_job_failed)
def job_error_hook(
    sender: type[models.core.BaseJob],
    instance: models.core.BaseJob,
    error_message: str,
    traceback: str,
    exception: Exception | None,
    **kwargs,
) -> None:
    """Present an example of job error hook."""
    logging.getLogger(__name__).warning(f"{instance}, {error_message}")
