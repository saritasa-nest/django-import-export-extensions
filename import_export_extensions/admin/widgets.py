
from django import forms
from django.template.loader import render_to_string


class ProgressBarWidget(forms.Widget):
    """Widget for progress bar field.

    Value for `progress_bar` element is changed using JS code.

    """

    template_name = "admin/import_export_extensions/progress_bar.html"

    def __init__(self, *args, **kwargs):
        """Get ``ImportJob`` or ``ExportJob`` instance from kwargs.

        ``ImportJob`` or ``ExportJob`` instance is used
        to render hidden element in `render` method.

        """
        self.job = kwargs.pop("job")
        self.url = kwargs.pop("url")
        super().__init__(*args, **kwargs)

    def render(self, *args, **kwargs) -> str:
        """Render HTML5 `progress` element.

        Additionally, method provides hidden `import_job_url` and
        `export_job_url` value that is used in `js/admin/progress_bar.js`
        to send GET requests.

        """
        return render_to_string(self.template_name, {"job_url": self.url})

    class Media:
        """Class with custom assets for widget."""

        css = dict(
            all=("import_export_extensions/css/widgets/progress_bar.css",),
        )
        js = (
            "admin/js/jquery.init.js",
            "import_export_extensions/js/widgets/progress_bar.js",
        )
