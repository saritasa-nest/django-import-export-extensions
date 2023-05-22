from django import forms
from django.urls import reverse

from ... import models
from ..widgets import ProgressBarWidget


class ImportJobAdminForm(forms.ModelForm):
    """Admin form for ``ImportJob`` model.

    Adds custom `import_progressbar` field that displays current import
    progress using AJAX requests to specified endpoint. Fields widget is
    defined in `__init__` method.

    """

    import_progressbar = forms.Field(
        required=False,
    )

    def __init__(
        self,
        instance: models.ImportJob,
        *args,
        **kwargs,
    ):
        """Provide `import_progressbar` widget the ``ImportJob`` instance."""
        super().__init__(*args, instance=instance, **kwargs)
        url_name = "admin:import_job_progress"
        self.fields["import_progressbar"].label = (
            "Import progress" if
            instance.import_status == models.ImportJob.ImportStatus.IMPORTING
            else "Parsing progress"
        )
        self.fields["import_progressbar"].widget = ProgressBarWidget(
            job=instance,
            url=reverse(url_name, args=(instance.id,)),
        )

    class Meta:
        fields = (
            "import_status",
            "resource_path",
            "data_file",
            "resource_kwargs",
            "traceback",
            "error_message",
            "result",
            "parse_task_id",
            "import_task_id",
            "parse_finished",
            "import_started",
            "import_finished",
            "created_by",
            "created",
            "modified",
        )
