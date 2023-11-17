from typing import Any

from django import forms

from import_export import forms as base_forms


class ExtendedImportForm(base_forms.ImportForm):
    force_import = forms.BooleanField(
        required=False,
        initial=False,
    )
