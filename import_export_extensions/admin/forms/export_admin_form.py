from django import forms
from django.urls import reverse

from ... import models
from ..widgets import ProgressBarWidget


class ExportJobAdminForm(forms.ModelForm):
    """Admin form for `ExportJob` model.

    Adds custom `export_progressbar` field that displays current export
    progress using AJAX requests to specified endpoint. Fields widget is
    defined in `__init__` method.

    """

    export_progressbar = forms.Field(
        label="Export progress",
        required=False,
    )

    def __init__(
        self,
        instance: models.ExportJob,
        *args,
        **kwargs,
    ):
        """Provide `export_progressbar` widget the `ExportJob` instance."""
        super().__init__(*args, instance=instance, **kwargs)
        url_name = "admin:export_job_progress"
        self.fields["export_progressbar"].widget = ProgressBarWidget(
            job=instance,
            url=reverse(url_name, args=(instance.id,)),
        )

    class Meta:
        fields = (
            "export_status",
            "resource_path",
            "file_format_path",
            "data_file",
            "resource_kwargs",
            "traceback",
            "error_message",
            "result",
            "export_task_id",
            "export_started",
            "export_finished",
            "created_by",
            "created",
            "modified",
        )
