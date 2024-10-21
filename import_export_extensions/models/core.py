import typing

from django.conf import settings
from django.db import models
from django.utils import module_loading
from django.utils.translation import gettext_lazy as _

from import_export.results import Result
from picklefield.fields import PickledObjectField


class CreationDateTimeField(models.DateTimeField):
    """DateTimeField to indicate created datetime.

    By default, sets editable=False, blank=True, auto_now_add=True.

    """

    def __init__(self, **kwargs):
        super().__init__(
            auto_now=True,
            verbose_name=_("Created"),
        )


class ModificationDateTimeField(models.DateTimeField):
    """DateTimeField  to indicate modified datetime.

    By default, sets editable=False, blank=True, auto_now=True.

    Sets value to now every time the object is saved.

    """

    def __init__(self, **kwargs):
        super().__init__(
            auto_now=True,
            verbose_name=_("Modified"),
        )


class TimeStampedModel(models.Model):
    """Model which tracks creation and modification time.

    An abstract base class model that provides self-managed "created" and
    "modified" fields.

    """

    created = CreationDateTimeField()
    modified = ModificationDateTimeField()

    class Meta:
        abstract = True


class TaskStateInfo(typing.TypedDict):
    """Class representing task state dict.

    Possible states:
        1. PENDING
        2. STARTED
        3. SUCCESS
        4. EXPORTING - custom status that also set export info

    https://docs.celeryproject.org/en/latest/userguide/tasks.html#states

    """

    state: str
    info: dict[str, int] | None


class BaseJob(TimeStampedModel):
    """Base model for managing celery jobs."""

    resource_path = models.CharField(
        max_length=128,
        verbose_name=_("Resource class path"),
        help_text=_(
            "Dotted path to subclass of `import_export.Resource` that "
            "should be used for import",
        ),
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
        help_text=_("Python traceback in case of import/export error"),
    )
    error_message = models.CharField(
        max_length=128,
        blank=True,
        default=str,
        verbose_name=_("Error message"),
        help_text=_("Python error message in case of import/export error"),
    )
    created_by = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        editable=False,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Created by"),
        help_text=_("User which started job"),
    )
    result = PickledObjectField(
        default=Result,
        verbose_name=_("Job result"),
        help_text=_(
            "Internal job result object that contain "
            "info about job statistics. Pickled Python object",
        ),
    )

    class Meta:
        abstract = True

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
    def progress(self) -> TaskStateInfo | None:
        """Return dict with current job state."""
        raise NotImplementedError
