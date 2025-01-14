import collections.abc
import typing

from rest_framework import request, serializers

from celery import states

from ... import models, resources
from .progress import ProgressSerializer


class ExportProgressSerializer(ProgressSerializer):
    """Serializer to show ExportJob progress."""

    state = serializers.ChoiceField(
        choices=[
            *models.ExportJob.ExportStatus.values,
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

    resource_class: type[resources.CeleryModelResource]

    def __init__(
        self,
        *args,
        ordering: collections.abc.Sequence[str] | None = None,
        filter_kwargs: dict[str, typing.Any] | None = None,
        resource_kwargs: dict[str, typing.Any] | None = None,
        **kwargs,
    ):
        """Set ordering, filter kwargs and current user."""
        super().__init__(*args, **kwargs)
        self._ordering = ordering
        self._filter_kwargs = filter_kwargs
        self._resource_kwargs = resource_kwargs or {}
        self._request: request.Request = self.context.get("request")
        self._user = getattr(self._request, "user", None)

    def validate(self, attrs: dict[str, typing.Any]) -> dict[str, typing.Any]:
        """Check that ordering and filter kwargs are valid."""
        self.resource_class(
            ordering=self._ordering,
            filter_kwargs=self._filter_kwargs,
            created_by=self._user,
            **self._resource_kwargs,
        ).get_queryset()
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
                ordering=self._ordering,
                filter_kwargs=self._filter_kwargs,
                **self._resource_kwargs,
            ),
            created_by=self._user,
        )

    def update(self, instance, validated_data):
        """Empty method to pass linters checks."""


# Use it to cache already generated serializers to avoid duplication
_GENERATED_EXPORT_JOB_SERIALIZERS: dict[
    type[resources.CeleryModelResource],
    type,
] = {}


def get_create_export_job_serializer(
    resource: type[resources.CeleryModelResource],
) -> type:
    """Create serializer for ExportJobs creation."""
    if resource in _GENERATED_EXPORT_JOB_SERIALIZERS:
        return _GENERATED_EXPORT_JOB_SERIALIZERS[resource]

    class _CreateExportJob(CreateExportJob):
        """Serializer to start export job."""

        resource_class: type[resources.CeleryModelResource] = resource
        file_format = serializers.ChoiceField(
            required=True,
            choices=[
                supported_format().get_extension()
                for supported_format in resource.SUPPORTED_FORMATS
            ],
        )

    _GENERATED_EXPORT_JOB_SERIALIZERS[resource] = type(
        f"{resource.__name__}CreateExportJob",
        (_CreateExportJob,),
        {},
    )
    return _GENERATED_EXPORT_JOB_SERIALIZERS[resource]
