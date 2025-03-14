import collections
import contextlib

from rest_framework import (
    decorators,
    exceptions,
    mixins,
    permissions,
    response,
    status,
    viewsets,
)

from ... import models
from .. import mixins as core_mixins


class BaseImportJobViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Base viewset for managing import jobs."""

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = core_mixins.ImportStartActionMixin.import_detail_serializer_class  # noqa: E501
    queryset = models.ImportJob.objects.all()
    search_fields: collections.abc.Sequence[str] = ("id",)
    ordering: collections.abc.Sequence[str] = (
        "id",
    )
    ordering_fields: collections.abc.Sequence[str] = (
        "id",
        "created",
        "modified",
    )

    def __init_subclass__(cls) -> None:
        """Dynamically create an cancel api endpoints.

        Need to do this to enable action and correct open-api spec generated by
        drf_spectacular.

        """
        super().__init_subclass__()
        decorators.action(
            methods=["POST"],
            detail=True,
        )(cls.cancel)
        decorators.action(
            methods=["POST"],
            detail=True,
        )(cls.confirm)
        # Correct specs of drf-spectacular if it is installed
        with contextlib.suppress(ImportError):
            from drf_spectacular.utils import extend_schema, extend_schema_view
            if hasattr(cls, "get_import_detail_serializer_class"):
                response_serializer = cls().get_import_detail_serializer_class()  # noqa: E501
            else:
                response_serializer = cls().get_serializer_class()
            extend_schema_view(
                cancel=extend_schema(
                    request=None,
                    responses={
                        status.HTTP_200_OK: response_serializer,
                    },
                ),
                confirm=extend_schema(
                    request=None,
                    responses={
                        status.HTTP_200_OK: response_serializer,
                    },
                ),
            )(cls)

    def confirm(self, *args, **kwargs):
        """Confirm import job that has `parsed` status."""
        job: models.ImportJob = self.get_object()

        try:
            job.confirm_import()
        except ValueError as error:
            raise exceptions.ValidationError(error.args[0]) from error

        serializer = self.get_serializer(instance=job)
        return response.Response(
            status=status.HTTP_200_OK,
            data=serializer.data,
        )

    def cancel(self, *args, **kwargs):
        """Cancel import job that is in progress."""
        job: models.ImportJob = self.get_object()

        try:
            job.cancel_import()
        except ValueError as error:
            raise exceptions.ValidationError(error.args[0]) from error

        serializer = self.get_serializer(instance=job)
        return response.Response(
            status=status.HTTP_200_OK,
            data=serializer.data,
        )

class ImportJobViewSet(
    core_mixins.ImportStartActionMixin,
    BaseImportJobViewSet,
):
    """Base API viewset for ImportJob model.

    Based on resource_class it will generate an endpoint which will allow to
    start an import to model which was specified in resource_class. On success
    this endpoint we return an instance of import.

    Endpoints:
        list - to get list of all import jobs
        details(retrieve) - to get status of import job
        start - create import job and start parsing data from attached file
        confirm - confirm import after parsing process is finished
        cancel - stop importing/parsing process and cancel this import job

    """

    import_action_name = "start"
    import_action_url = "start"

    def get_queryset(self):
        """Filter import jobs by resource used in viewset."""
        if self.action == getattr(self, "import_action", ""):
            # To make it consistent and for better support of drf-spectacular
            return super().get_queryset()  # pragma: no cover
        return super().get_queryset().filter(
            resource_path=self.resource_class.class_path,
        )

class ImportJobForUserViewSet(
    core_mixins.LimitQuerySetToCurrentUserMixin,
    ImportJobViewSet,
):
    """Viewset for providing import feature to users."""

class BaseImportJobForUserViewSet(
    core_mixins.LimitQuerySetToCurrentUserMixin,
    BaseImportJobViewSet,
):
    """Viewset for providing export job management to users."""
