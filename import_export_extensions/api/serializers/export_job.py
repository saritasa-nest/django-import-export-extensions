import typing

from rest_framework import request, serializers

from celery import states
from django_filters.utils import translate_validation

from ... import models, resources
from .progress import ProgressSerializer


class ExportProgressSerializer(ProgressSerializer):
    """Serializer to show ExportJob progress."""

    state = serializers.ChoiceField(
        choices=models.ExportJob.ExportStatus.values
        + [
            states.PENDING,
            states.STARTED,
            states.SUCCESS,
        ],
    )


class ExportJobSerializer(serializers.ModelSerializer):
    """Serializer to show information about export job."""

    progress = ExportProgressSerializer()

    class Meta:
        model = models.ExportJob
        fields = (
            "id",
            "export_status",
            "data_file",
            "progress",
            "export_started",
            "export_finished",
            "created",
            "modified",
        )


class CreateExportJob(serializers.Serializer):
    """Base Serializer to start export job.

    It used to set up base workflow of ExportJob creation via API.

    """

    resource_class: typing.Type[resources.CeleryModelResource]

    def __init__(
        self,
        *args,
        filter_kwargs: typing.Optional[dict[str, typing.Any]] = None,
        resource_kwargs: typing.Optional[dict[str, typing.Any]] = None,
        **kwargs,
    ):
        """Set filter kwargs and current user."""
        super().__init__(*args, **kwargs)
        self._filter_kwargs = filter_kwargs
        self._resource_kwargs = resource_kwargs or {}
        self._request: request.Request = self.context.get("request")
        self._user = getattr(self._request, "user", None)

    def validate(self, attrs: dict[str, typing.Any]) -> dict[str, typing.Any]:
        """Check that filter kwargs are valid."""
        if not self._filter_kwargs:
            return attrs

        filter_instance = self.resource_class.filterset_class(
            data=self._filter_kwargs,
        )
        if not filter_instance.is_valid():
            raise translate_validation(error_dict=filter_instance.errors)
        return attrs

    def create(
        self,
        validated_data: dict[str, typing.Any],
    ) -> models.ExportJob:
        """Create export job."""
        file_format_class = self.resource_class.get_supported_extensions_map()[
            validated_data["file_format"]
        ]
        return models.ExportJob.objects.create(
            resource_path=self.resource_class.class_path,
            file_format_path=f"{file_format_class.__module__}.{file_format_class.__name__}",
            resource_kwargs=dict(
                filter_kwargs=self._filter_kwargs,
                **self._resource_kwargs,
            ),
            created_by=self._user,
        )

    def update(self, instance, validated_data):
        """Empty method to pass linters checks."""


def get_create_export_job_serializer(
    resource: typing.Type[resources.CeleryModelResource],
) -> typing.Type:  # type: ignore
    """Create serializer for ExportJobs creation."""

    class _CreateExportJob(CreateExportJob):
        """Serializer to start export job."""

        resource_class: typing.Type[resources.CeleryModelResource] = resource
        file_format = serializers.ChoiceField(
            required=True,
            choices=[
                supported_format().get_extension()
                for supported_format in resource.SUPPORTED_FORMATS
            ],
        )

    return type(
        f"{resource.__name__}CreateExportJob",
        (_CreateExportJob,),
        {},
    )
