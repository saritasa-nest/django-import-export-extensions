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


class ExportBase(type):
    """Add custom create action for each ExportJobViewSet."""

    def __new__(cls, name, bases, attrs, **kwargs):
        """Dynamically create an export start api endpoint.

        We need this to specify on fly action's filterset_class and queryset
        (django-filters requires view's queryset and filterset_class's
        queryset model to match). Also, if drf-spectacular is installed
        specify request and response, and enable filters.

        """
        viewset: typing.Type["ExportJobViewSet"] = super().__new__(
            cls,
            name,
            bases,
            attrs,
            **kwargs,
        )
        # Skip if it is a base viewset, since none of needed class attrs are
        # specified
        if name == "ExportJobViewSet":
            return viewset

        def start(self: "ExportJobViewSet", request: Request):
            """Validate request data and start ExportJob."""
            serializer = self.get_serializer(
                data=request.data,
                filter_kwargs=request.query_params,
            )
            serializer.is_valid(raise_exception=True)
            export_job = serializer.save()
            return response.Response(
                data=self.get_detail_serializer_class()(
                    instance=export_job,
                ).data,
                status=status.HTTP_201_CREATED,
            )

        viewset.start = decorators.action(
            methods=["POST"],
            detail=False,
            queryset=viewset.resource_class.get_model_queryset(),
            filterset_class=getattr(
                viewset.resource_class, "filterset_class", None,
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
                    request=viewset().get_export_create_serializer_class(),
                    responses={
                        status.HTTP_201_CREATED: detail_serializer_class,
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


class ExportJobViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
    metaclass=ExportBase,
):
    """Base API viewset for ExportJob model.

    Based on resource_class it will generate an endpoint which will allow to
    start an export of model which was specified in resource_class. This
    endpoint will support filtration based on FilterSet class specified in
    resource. On success this endpoint we return an instance of export, to
    get status of job, just use detail(retrieve) endpoint.

    """

    permission_classes = (permissions.IsAuthenticated,)
    queryset = models.ExportJob.objects.all()
    serializer_class = serializers.ExportJobSerializer
    resource_class: typing.Optional[
        typing.Type[resources.CeleryModelResource]
    ] = None
    filterset_class: django_filters.rest_framework.FilterSet = None

    def get_queryset(self):
        """Filter export jobs by resource used in viewset."""
        return super().get_queryset().filter(
            resource_path=self.resource_class.class_path,
        )

    def get_resource_kwargs(self) -> dict[str, typing.Any]:
        """Provide extra arguments to resource class."""
        return {}

    def get_serializer(self, *args, **kwargs):
        """Provide resource kwargs to serializer class."""
        if self.action == "start":
            kwargs.setdefault("resource_kwargs", self.get_resource_kwargs())
        return super().get_serializer(*args, **kwargs)

    def get_serializer_class(self):
        """Return special serializer on creation."""
        if self.action == "start":
            return self.get_export_create_serializer_class()
        return self.get_detail_serializer_class()

    def get_detail_serializer_class(self):
        """Get serializer which will be used show details of export job."""
        return self.serializer_class

    def get_export_create_serializer_class(self):
        """Get serializer which will be used to start export job."""
        return serializers.get_create_export_job_serializer(
            self.resource_class,
        )

    @decorators.action(methods=["POST"], detail=True)
    def cancel(self, *args, **kwargs):
        """Cancel export job that is in progress."""
        job: models.ExportJob = self.get_object()

        try:
            job.cancel_export()
        except ValueError as error:
            raise ValidationError(error.args[0])

        serializer = self.get_serializer(instance=job)
        return response.Response(
            status=status.HTTP_200_OK,
            data=serializer.data,
        )
