"""This is source code of origin application ``django-import-export``.

The difference is that these forms don't required file format, it is taken from
file. And in ExportForm the default export format is `xlsx`.

"""
import typing

from django import forms
from django.utils.translation import gettext_lazy as _

from import_export.formats import base_formats


class ImportForm(forms.Form):
    """Form for creating import."""

    import_file = forms.FileField(
        label=_("File to import"),
    )


class ExportForm(forms.Form):
    """Form for exporting."""

    file_format = forms.ChoiceField(
        label=_("Choose format"),
        choices=(),
    )

    def __init__(
        self,
        formats: list[typing.Type[base_formats.Format]],
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        choices = []
        initial_choice = 0
        for index, export_format in enumerate(formats):
            extension = export_format().get_title()
            if extension.lower() == "xlsx":
                initial_choice = index
            choices.append((str(index), extension))
        if len(formats) > 1:
            choices.insert(0, ("", "---"))

        self.fields["file_format"].choices = choices
        self.fields["file_format"].initial = initial_choice
