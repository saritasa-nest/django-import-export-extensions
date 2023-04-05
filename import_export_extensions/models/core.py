import typing

from django.db import models
from django.utils.translation import gettext_lazy as _


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
    """Class representing task state dict."""
    state: str
    info: typing.Optional[dict[str, int]]
