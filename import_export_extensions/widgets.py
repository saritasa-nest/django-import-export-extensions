import mimetypes
import typing
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.core.files import File
from django.core.files.storage import default_storage
from django.db.models import Model, Q, QuerySet
from django.db.models.fields.files import FieldFile
from django.forms import ValidationError
from django.utils.encoding import smart_str

from import_export.exceptions import ImportExportError
from import_export.widgets import CharWidget, ManyToManyWidget

from . import models, utils

DEFAULT_SYSTEM_STORAGE = "django.core.files.storage.FileSystemStorage"


class IntermediateManyToManyWidget(ManyToManyWidget):
    """Widget for M2M field with custom ``through`` model.

    Default M2M widget store just IDs of related objects.
    With intermediate model additional data may be stored.

    This widget (and subclasses) should be used with
    ``IntermediateManyToManyField``. This field expects that widget will return
    plain data for intermediate model as a dict.

    Example models from ``IntermediateManyToManyField`` docstring will be used.

    So this widget's ``clean`` method should return dict with Membership info,
    i.e::

        {
            'band': <Some band>,
            'date_joined': '2015-01-18'
        }

    And ``render`` method should return string that will contain required data.

    """

    def __init__(
        self,
        rem_model: type[Model],
        instance_separator: str = ",",
        prop_separator: str | None = None,
        rem_field: str = "pk",
        rem_field_lookup: str | None = None,
        extra_fields: list[str] | None = None,
        render_empty: bool = False,
        *args,
        **kwargs,
    ):
        """Init widget.

        Args:
            rem_model(models.Model): remote model (i.e. Band)
            instance_separator(str): separator for instances
            prop_separator(str): separator for instance properties
            rem_field(str): name of remote field to dump remote model (pk
                by default, may be used more human-readable names)
            extra_fields(list[str]): extra fields that should be dumped
                (will be dumped in most dummy way)
            render_empty (bool): defines if render empty values or not

        """
        if prop_separator == ";" or prop_separator is None:
            prop_separator = ":"
        self.rem_model = rem_model
        self.instance_separator = instance_separator
        self.prop_separator = prop_separator
        self.rem_field = rem_field
        self.rem_field_lookup = rem_field_lookup
        self.extra_fields = extra_fields or []
        self.render_empty = render_empty

    def render(
        self,
        value: typing.Iterable[Model],
        obj=None,
        *args,
        **kwargs,
    ) -> str:
        """Return an export representation of a intermediate instances.

        For artists example should be returned something like
            "5:1990-12-12;19:2005-08-16"
            where 5 is band id

        Args:
            value(QuerySet): instances of intermediate model

        """
        instances = [
            self.render_instance(i, self._get_related_instance(i))
            for i in value
        ]
        # Clean empty instances
        if not self.render_empty:
            instances = list(filter(None, instances))

        return self.instance_separator.join(instances)

    def render_instance(self, instance: Model, related_object: Model) -> str:
        """Return export representation of one intermediate instance.

        Should take related object PK and extra fields from Intermediate model,
        i.e. Artist.pk and Membership.date_joined

        Args:
            instance: object of intermediate model
            related_object: associated object (i.e. Band)

        """
        # get related object (i.e. Band)
        props = [
            smart_str(self._get_field_value(related_object, self.rem_field)),
            *[
                smart_str(self._get_field_value(instance, attr))
                for attr in self.extra_fields
            ],
        ]

        return self.prop_separator.join(props)

    def _get_field_value(self, obj: Model, field: str) -> typing.Any:
        """Get `field` value from an object.

        Support chained fields like `field1__field2__field3` which allows to
        get values from obj.field1.field2.field3

        """
        fields_chain = field.split("__")
        value = obj
        for s in fields_chain:
            value = getattr(value, s)

        return value

    def _get_related_instance(self, instance: Model) -> Model:
        """Get related instance based on IntermediateModel instance.

        i.e. get Band based on Membership instance

        Args:
            instance: instance of intermediate model

        """
        for field in instance._meta.get_fields():
            if field.related_model == self.rem_model:
                return getattr(instance, field.name)

    def clean(
        self,
        value: str,
        *args,
        **kwargs,
    ) -> list[dict[str, typing.Any]]:
        """Restore data from dump.

        In ``value`` we have data that saved using ``render`` method. We should
        restore it

        Args:
            value(str): rendered data about instance of intermediate model
            instance:

        Returns:
            list[dict]: parsed data

        Example:
            [{'band': <Band object>, 'date_joined': '1998-12-21'}]

        """
        if not value:
            return []  # pragma: no cover

        # if value is one integer number
        value = str(value)

        # in some cases if click `enter` values `\n\r` inserted
        if self.instance_separator == "\n":  # pragma: no cover
            value = value.replace("\r", "")

        raw_instances = utils.clean_sequence_of_string_values(
            value.split(self.instance_separator),
        )

        result = []
        invalid_instances = []
        restored_objects_ids = []
        for raw_instance in raw_instances:
            try:
                for item in self.clean_instance(raw_instance):
                    if item["object"].pk not in restored_objects_ids:
                        restored_objects_ids.append(item["object"].pk)
                        result.append(item)
            except ValueError:
                invalid_instances.append(raw_instance)

        # if there are entries in `invalid_instances`
        if invalid_instances:
            raise ValueError(
                f"You are trying import invalid values: {invalid_instances!s}",
            )

        return result

    def clean_instance(self, raw_instance: str) -> list[dict[str, typing.Any]]:
        """Restore info about one instance of intermediate model.

        If there are few instances in DB with same
        `self.rem_field`=`rem_field_value` then it returns few items

        Args:
            raw_instance(str): info about one instance that saved using
                ``render_instance`` method

        Returns:
            list: list of dicts with restored info about one intermediate
                  instance. If there are few instances in DB with same
                  `self.rem_field`=`rem_field_value` then it returns few items

        Example::

            {
                'object': <Band object>,
                'properties': {'date_joined': '2011-10-12'}
            }

        """
        props = raw_instance.split(self.prop_separator)

        if len(props) > len(self.extra_fields) + 1:
            # +1 is for `self.rem_field`
            raise ImportExportError(
                f"Too many property separators '{self.prop_separator}' in "
                f"'{raw_instance}'",
            )

        # rem instance now contains value used to identify related object,
        # i.e. PK of Band
        # props contain other saved properties of intermediate model
        # i.e. `date_joined`
        rem_field_value, *props = utils.clean_sequence_of_string_values(
            raw_instance.split(self.prop_separator),
            ignore_empty=False,
        )

        # get related objects
        qs = self.filter_instances(rem_field_value)

        # if we tries import nonexistent instance
        if not qs.exists():
            raise ValueError(f"Invalid instance {raw_instance}")

        # build dict with other properties. Ignore extra fields which has
        # empty strings values
        other_props = {
            key: value
            for key, value in zip(self.extra_fields, props, strict=False)
            if value
        }
        return [
            {"object": rem_object, "properties": other_props}
            for rem_object in qs
        ]

    def filter_instances(self, rem_field_value: str) -> QuerySet:
        """Shortcut to filter corresponding instances."""
        if self.rem_field_lookup:
            if self.rem_field_lookup == "regex":
                instance_filter = utils.get_clear_q_filter(
                    rem_field_value,
                    self.rem_field,
                )
            else:
                lookup = f"{self.rem_field}__{self.rem_field_lookup}"
                instance_filter = Q(**{lookup: rem_field_value})
        else:
            instance_filter = Q(**{self.rem_field: rem_field_value})

        return self.rem_model.objects.filter(instance_filter)


class FileWidget(CharWidget):
    """Widget for working with File fields."""

    def __init__(self, filename: str):
        self.filename = filename

    def render(
        self,
        value: FieldFile | None,
        obj=None,
        **kwargs,
    ) -> str | None:
        """Convert DB value to URL to file."""
        if not value:
            return None

        if self._get_default_storage() == DEFAULT_SYSTEM_STORAGE:
            return f"http://localhost:8000{value.url}"

        return value.url

    def clean(
        self,
        value: str | None,
        *args,
        **kwargs,
    ) -> str | None:
        """Get the file and check for exists."""
        if not value:
            return None

        internal_url = utils.url_to_internal_value(urlparse(value).path)

        if not internal_url:
            raise ValidationError("Invalid file path")

        try:
            if default_storage.exists(internal_url):
                return internal_url
        except SuspiciousFileOperation:  # pragma: no cover
            pass

        return self._get_file(value)

    def _get_file(self, url: str) -> File:
        """Download file from the external resource."""
        file = utils.download_file(url)
        ext = mimetypes.guess_extension(file.content_type)
        filename = f"{self.filename}.{ext}" if ext else self.filename

        return File(file, filename)

    def _get_default_storage(self) -> str:
        """Return default system storage used in project.

        Use the value from `STORAGES` if it's available,
        otherwise use `DEFAULT_FILE_STORAGE`.

        `STORAGES` variable replaced `DEFAULT_FILE_STORAGE`, in django 4.2
        https://docs.djangoproject.com/en/4.2/ref/settings/#default-file-storage

        """
        if hasattr(settings, "STORAGES"):
            return settings.STORAGES.get(
                models.tools.IMPORT_EXPORT_STORAGE_ALIAS,
                settings.STORAGES["default"],
            )["BACKEND"]
        return settings.DEFAULT_FILE_STORAGE  # pragma: no cover
