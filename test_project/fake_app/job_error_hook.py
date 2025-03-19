import logging

from import_export_extensions.models.core import BaseJob


def job_error_hook(
    instance: BaseJob,
    error_message: str,
    traceback: str,
    exception: Exception | None,
):
    """Present an example of job error hook."""
    logging.getLogger(__file__).warning(f"{instance}, {error_message}")
