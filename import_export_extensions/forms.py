"""This is source code of origin application ``django-import-export``.

The difference is that these forms don't required file format, it is taken from
file. And in ExportForm the default export format is `xlsx`.

"""
import typing

from django import forms
from django.utils.translation import gettext_lazy as _

from import_export.formats import base_formats

FormatType = typing.Type[base_formats.Format]


class ImportExportFormBase(forms.Form):
    """Provide common logic for export/import form."""

    resource = forms.ChoiceField(
        label=_("Resource"),
        choices=(),
        required=False,
    )

    def __init__(self, *args, resources=None, **kwargs):
        super().__init__(*args, **kwargs)
        if resources and len(resources) > 1:
            resource_choices = []
            for index, resource in enumerate(resources):
                resource_choices.append((index, resource.__name__))
            self.fields["resource"].choices = resource_choices
        else:
            del self.fields["resource"]


class ImportForm(ImportExportFormBase):
    """Form for creating import."""

    import_file = forms.FileField(
        label=_("File to import"),
    )


class ExportForm(ImportExportFormBase):
    """Form for exporting."""

    file_format = forms.ChoiceField(
        label=_("Choose format"),
        choices=(),
    )

    class Media:
        js = ["import_export_extensions/js/admin/export_form.js"]

    def __init__(
        self,
        formats: typing.Optional[list[FormatType]] = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        resource_classes = kwargs.get("resources")
        if not (formats or resource_classes):
            raise Exception("'formats' and 'resources' can't both be None.")
        if not resource_classes:
            export_formats = formats
        else:
            export_formats = resource_classes[0].get_export_formats()
        if self.data and "resource" in self.data:
            try:
                resource_index = int(self.data["resource"])
                resource_class = resource_classes[resource_index]
            except (ValueError, IndexError, TypeError):
                pass
            else:
                export_formats = resource_class.get_export_formats()
        choices = []
        initial_choice = 0
        for index, export_format in enumerate(export_formats):  # type: ignore
            extension = export_format().get_title()
            if extension.lower() == "xlsx":
                initial_choice = index
            choices.append((str(index), extension))
        if len(export_formats) > 1:     # type: ignore
            choices.insert(0, ("", "---"))

        self.fields["file_format"].choices = choices
        self.fields["file_format"].initial = initial_choice
