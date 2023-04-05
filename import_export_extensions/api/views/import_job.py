import typing

from rest_framework import (
    decorators,
    mixins,
    permissions,
    response,
    status,
    viewsets,
)
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request

import django_filters

from ... import models, resources
from .. import serializers


class ImportBase(type):
    """Add custom create action for each ImportJobViewSet."""

    def __new__(cls, name, bases, attrs, **kwargs):
        """Dynamically create an import start api endpoint.

        We need this to specify on fly action's filterset_class and queryset
        (django-filters requires view's queryset and filterset_class's
        queryset model to match). Also, if drf-spectacular is installed
        specify request and response, and enable filters.

        """
        viewset: typing.Type["ImportJobViewSet"] = super().__new__(
            cls,
            name,
            bases,
            attrs,
            **kwargs,
        )
        # Skip if it is a base viewset, since none of needed class attrs are
        # specified
        if name == "ImportJobViewSet":
            return viewset

        def start(self: "ImportJobViewSet", request: Request):
            """Validate request data and start ImportJob."""
            serializer = self.get_serializer(
                data=request.data,
                filter_kwargs=request.query_params,
            )
            serializer.is_valid(raise_exception=True)
            import_job = serializer.save()
            return response.Response(
                data=self.get_detail_serializer_class()(
                    instance=import_job,
                ).data,
                status=status.HTTP_201_CREATED,
            )

        viewset.start = decorators.action(
            methods=["POST"],
            detail=False,
            queryset=viewset.resource_class.get_model_queryset(),
            filterset_class=getattr(
                viewset.resource_class, "filter_class", None,
            ),
            filter_backends=[
                django_filters.rest_framework.DjangoFilterBackend,
            ],
        )(start)
        # Correct specs of drf-spectacular if it is installed
        try:
            from drf_spectacular.utils import extend_schema, extend_schema_view

            detail_serializer_class = viewset().get_detail_serializer_class()
            return extend_schema_view(
                start=extend_schema(
                    filters=True,
                    request=viewset().get_import_create_serializer_class(),
                    responses={
                        status.HTTP_201_CREATED: detail_serializer_class,
                    },
                ),
                confirm=extend_schema(
                    request=None,
                    responses={
                        status.HTTP_200_OK: detail_serializer_class,
                    },
                ),
                cancel=extend_schema(
                    request=None,
                    responses={
                        status.HTTP_200_OK: detail_serializer_class,
                    },
                ),
            )(viewset)
        except ImportError:
            pass
        return viewset


class ImportJobViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
    metaclass=ImportBase,
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

    permission_classes = (permissions.IsAuthenticated,)
    queryset = models.ImportJob.objects.all()
    serializer_class = serializers.ImportJobSerializer
    resource_class: typing.Optional[
        typing.Type[resources.CeleryModelResource]
    ] = None
    filterset_class: django_filters.rest_framework.FilterSet = None

    def get_queryset(self):
        """Filter import jobs by resource used in viewset."""
        return super().get_queryset().filter(
            resource_path=self.resource_class.class_path,
        )

    def get_serializer_class(self):
        """Return special serializer on creation."""
        if self.action == "start":
            return self.get_import_create_serializer_class()
        return self.get_detail_serializer_class()

    def get_detail_serializer_class(self):
        """Get serializer which will be used show details of import job."""
        return self.serializer_class

    def get_import_create_serializer_class(self):
        """Get serializer which will be used to start import job."""
        return serializers.get_create_import_job_serializer(
            self.resource_class,
        )

    @decorators.action(methods=["POST"], detail=True)
    def confirm(self, *args, **kwargs):
        """Confirm import job that has `parsed` status."""
        job: models.ImportJob = self.get_object()

        try:
            job.confirm_import()
        except ValueError:
            raise ValidationError(
                f"Wrong import job status: {job.import_status}",
            )

        serializer = self.get_serializer(instance=job)
        return response.Response(
            status=status.HTTP_200_OK,
            data=serializer.data,
        )

    @decorators.action(methods=["POST"], detail=True)
    def cancel(self, *args, **kwargs):
        """Cancel import job that is in progress."""
        job: models.ImportJob = self.get_object()

        try:
            job.cancel_import()
        except ValueError:
            raise ValidationError(
                f"Wrong import job status: {job.import_status}",
            )

        serializer = self.get_serializer(instance=job)
        return response.Response(
            status=status.HTTP_200_OK,
            data=serializer.data,
        )
