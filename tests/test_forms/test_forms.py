from import_export.formats import base_formats as formats

from import_export_extensions import forms


def test_export_form_set_xlsx_as_initial_choice():
    """Ensure xlsx is initial choice for export form."""
    available_formats = [
        formats.CSV,
        formats.XLS,
        formats.XLSX,
        formats.JSON,
    ]
    export_form = forms.ExportForm(formats=available_formats)
    initial_choice = export_form.fields["file_format"].initial
    xlsx_choice_index = available_formats.index(formats.XLSX)

    assert initial_choice == xlsx_choice_index
