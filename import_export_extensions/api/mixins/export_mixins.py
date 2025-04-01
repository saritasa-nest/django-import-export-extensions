import collections.abc
import contextlib
import typing

from django.conf import settings
from django.utils import module_loading

from rest_framework import (
    decorators,
    request,
    response,
    status,
)

from ... import resources
from .. import serializers


class ExportStartActionMixin:
    """Mixin which adds start export action."""

    resource_class: type[resources.CeleryModelResource]
    export_action = "start_export_action"
    export_action_name = "export"
    export_action_url = "export"
    export_detail_serializer_class = serializers.ExportJobSerializer
    export_ordering: collections.abc.Sequence[str] = ()
    export_ordering_fields: collections.abc.Sequence[str] = ()
    export_open_api_description = (
        "This endpoint creates export job and starts it. "
        "To monitor progress use detail endpoint for jobs to fetch state of "
        "job. Once it's status is `EXPORTED`, you can download file."
    )

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        # Skip if it is has no resource_class specified
        if not hasattr(cls, "resource_class"):
            return
        filter_backends = [
            module_loading.import_string(
                settings.DRF_EXPORT_DJANGO_FILTERS_BACKEND,
            ),
        ]
        if cls.export_ordering_fields:
            filter_backends.append(
                module_loading.import_string(
                    settings.DRF_EXPORT_ORDERING_BACKEND,
                ),
            )

        def start_export_action(
            self: "ExportStartActionMixin",
            request: request.Request,
            *args,
            **kwargs,
        ) -> response.Response:
            return self.start_export(request)

        setattr(cls, cls.export_action, start_export_action)
        decorators.action(
            methods=["POST"],
            url_name=cls.export_action_name,
            url_path=cls.export_action_url,
            detail=False,
            queryset=cls.resource_class.get_model_queryset(),
            serializer_class=cls().get_export_create_serializer_class(),
            filterset_class=getattr(
                cls.resource_class,
                "filterset_class",
                None,
            ),
            filter_backends=filter_backends,
            ordering=cls.export_ordering,
            ordering_fields=cls.export_ordering_fields,
        )(getattr(cls, cls.export_action))
        # Correct specs of drf-spectacular if it is installed
        with contextlib.suppress(ImportError):
            from drf_spectacular import utils

            utils.extend_schema_view(
                **{
                    cls.export_action: utils.extend_schema(
                        description=cls.export_open_api_description,
                        filters=True,
                        responses={
                            status.HTTP_201_CREATED: cls().get_export_detail_serializer_class(),  # noqa: E501
                        },
                    ),
                },
            )(cls)

    def get_queryset(self):
        """Return export model queryset on export action.

        For better openapi support and consistency.

        """
        if self.action == self.export_action:
            return self.resource_class.get_model_queryset()  # pragma: no cover
        return super().get_queryset()

    def get_export_detail_serializer_class(self):
        """Get serializer which will be used show details of export job."""
        return self.export_detail_serializer_class

    def get_export_create_serializer_class(self):
        """Get serializer which will be used to start export job."""
        return serializers.get_create_export_job_serializer(
            self.resource_class,
        )

    def get_export_resource_kwargs(self) -> dict[str, typing.Any]:
        """Provide extra arguments to resource class."""
        return {}

    def get_serializer(self, *args, **kwargs):
        """Provide resource kwargs to serializer class."""
        if self.action == self.export_action:
            kwargs.setdefault(
                "resource_kwargs",
                self.get_export_resource_kwargs(),
            )
        return super().get_serializer(*args, **kwargs)

    def start_export(self, request: request.Request) -> response.Response:
        """Validate request data and start ExportJob."""
        ordering = request.query_params.get("ordering", "")
        if ordering:
            ordering = ordering.split(",")
        serializer = self.get_serializer(
            data=request.data,
            ordering=ordering,
            filter_kwargs=request.query_params,
        )
        serializer.is_valid(raise_exception=True)
        export_job = serializer.save()
        return response.Response(
            data=self.get_export_detail_serializer_class()(
                instance=export_job,
            ).data,
            status=status.HTTP_201_CREATED,
        )
