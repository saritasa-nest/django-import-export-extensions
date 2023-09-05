import typing

from rest_framework import request, serializers

from celery import states

from ... import models, resources
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

    class Meta:
        model = models.ImportJob
        fields = (
            "id",
            "import_status",
            "data_file",
            "progress",
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
