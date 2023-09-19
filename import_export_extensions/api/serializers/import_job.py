import typing

from rest_framework import request, serializers

from celery import states

from ... import models, resources
from . import import_job_details as details
from .progress import ProgressSerializer


class ImportProgressSerializer(ProgressSerializer):
    """Serializer to show ImportJob progress."""

    state = serializers.ChoiceField(
        choices=models.ImportJob.ImportStatus.values
        + [
            states.PENDING,
            states.STARTED,
            states.SUCCESS,
        ],
    )


class ImportJobSerializer(serializers.ModelSerializer):
    """Serializer to show information about import job."""

    progress = ImportProgressSerializer()

    import_params = details.ImportParamsSerializer(
        read_only=True,
        source="*",
    )
    totals = details.TotalsSerializer(
        read_only=True,
        source="*",
    )
    parse_error = serializers.CharField(
        source="error_message",
        read_only=True,
        allow_blank=True,
    )
    input_error = details.InputErrorSerializer(
        source="*",
        read_only=True,
    )
    importing_data = details.ImportingDataSerializer(
        read_only=True,
        source="*",
    )
    input_errors_file = serializers.FileField(
        read_only=True,
        allow_null=True,
    )
    is_all_rows_shown = details.IsAllRowsShowField(
        source="*",
        read_only=True,
    )

    class Meta:
        model = models.ImportJob
        fields = (
            "id",
            "progress",
            "import_status",
            "import_params",
            "totals",
            "parse_error",
            "input_error",
            "is_all_rows_shown",
            "importing_data",
            "input_errors_file",
            "import_started",
            "import_finished",
            "created",
            "modified",
        )


class CreateImportJob(serializers.Serializer):
    """Base Serializer to start import job.

    It used to set up base workflow of ImportJob creation via API.

    """

    resource_class: typing.Type[resources.CeleryModelResource]

    file = serializers.FileField(required=True)
    skip_parse_step = serializers.BooleanField(
        required=False,
        default=False,
    )

    def __init__(
        self,
        *args,
        resource_kwargs: typing.Optional[dict[str, typing.Any]] = None,
        **kwargs,
    ):
        """Set filter kwargs and current user."""
        super().__init__(*args, **kwargs)
        self._request: request.Request = self.context.get("request")
        self._resource_kwargs = resource_kwargs or {}
        self._user = getattr(self._request, "user", None)

    def create(
        self,
        validated_data: dict[str, typing.Any],
    ) -> models.ImportJob:
        """Create import job."""
        return models.ImportJob.objects.create(
            data_file=validated_data["file"],
            resource_path=self.resource_class.class_path,
            resource_kwargs=self._resource_kwargs,
            created_by=self._user,
            skip_parse_step=validated_data["skip_parse_step"],
        )

    def update(self, instance, validated_data):
        """Empty method to pass linters checks."""


def get_create_import_job_serializer(
    resource: typing.Type[resources.CeleryModelResource],
) -> typing.Type:  # type: ignore
    """Create serializer for ImportJobs creation."""

    class _CreateImportJob(CreateImportJob):
        """Serializer to start import job."""

        resource_class: typing.Type[resources.CeleryModelResource] = resource

    return type(
        f"{resource.__name__}CreateImportJob",
        (_CreateImportJob,),
        {},
    )
