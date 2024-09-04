from django import forms

from import_export import forms as base_forms


class ForceImportForm(base_forms.ImportForm):
    """Import form with `force_import` option."""

    force_import = forms.BooleanField(
        required=False,
        initial=False,
    )
