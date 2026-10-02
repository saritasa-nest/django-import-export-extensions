import collections.abc
import contextlib
import typing

from django.conf import settings
from django.db.models import QuerySet
from django.utils import module_loading
from rest_framework import (
    decorators as drf_decorators,
    permissions as drf_permissions,
    request as drf_request,
    response as drf_response,
    serializers as drf_serializers,
    settings as drf_settings,
    status as drf_status,
    throttling as drf_throttling,
)

from ... import resources
from .. import serializers


class ExportStartActionMixin:
    """Mixin which adds start export action."""

    resource_class: type[resources.CeleryModelResource]
    is_export_action: bool = False
    export_action = "start_export_action"
    export_action_name = "export"
    export_action_url = "export"
    export_detail_serializer_class = serializers.ExportJobSerializer
    export_ordering: collections.abc.Sequence[str] = ()
    export_ordering_fields: collections.abc.Sequence[str] = ()
    export_permission_classes: collections.abc.Sequence[
        type[drf_permissions.BasePermission]
    ] = ()
    export_throttle_classes: collections.abc.Sequence[
        type[drf_throttling.BaseThrottle]
    ] = ()
    throttle_scope: str | None = None
    export_throttle_scope: str = "export"
    export_open_api_description = (
        "This endpoint creates export job and starts it. "
        "To monitor progress use detail endpoint for jobs to fetch state of "
        "job. Once it's status is `EXPORTED`, you can download file."
    )

    def __init_subclass__(cls) -> None:
        """Set up `start_export_action` as action of viewset."""
        super().__init_subclass__()
        # Skip if it is has no resource_class specified
        if not hasattr(cls, "resource_class"):
            return

        def start_export_action(
            self: "ExportStartActionMixin",
            request: drf_request.Request,
            *args,
            **kwargs,
        ) -> drf_response.Response:
            return self.start_export(request)

        setattr(cls, cls.export_action, start_export_action)
        drf_decorators.action(
            methods=["POST"],
            detail=False,
            is_export_action=True,
            export_action_name=cls.export_action_name,
            export_action_url=cls.export_action_url,
            resource_class=cls.resource_class,
        )(getattr(cls, cls.export_action))

        for action_name in dir(cls):
            action_attr = getattr(cls, action_name)
            action_kwargs = getattr(action_attr, "kwargs", {})
            if action_kwargs.get("is_export_action"):
                cls.set_export_action(
                    action_name=action_name,
                    action_attr=action_attr,
                    action_kwargs=action_kwargs,
                )

    @classmethod
    def set_export_action(
        cls,
        action_name: str,
        action_attr: typing.Any,
        action_kwargs: dict[str, typing.Any],
    ) -> None:
        """Set up export action with proper attrs."""
        resource_class = action_kwargs["resource_class"]
        action_view = cls(**action_kwargs)
        filter_backends = [
            module_loading.import_string(
                settings.DRF_EXPORT_DJANGO_FILTERS_BACKEND,
            ),
        ]
        if action_view.export_ordering_fields:
            filter_backends.append(
                module_loading.import_string(
                    settings.DRF_EXPORT_ORDERING_BACKEND,
                ),
            )
        default_throttle_classes = (
            tuple(
                map(
                    module_loading.import_string,
                    settings.DRF_EXPORT_THROTTLE_CLASSES,
                ),
            )
            or drf_settings.api_settings.DEFAULT_THROTTLE_CLASSES
        )
        default_permission_classes = (
            tuple(
                map(
                    module_loading.import_string,
                    settings.DRF_EXPORT_PERMISSION_CLASSES,
                ),
            )
            or drf_settings.api_settings.DEFAULT_PERMISSION_CLASSES
        )
        action_attr.url_name = action_kwargs.get(
            "export_action_name",
            action_attr.url_name,
        )
        action_attr.url_path = action_kwargs.get(
            "export_action_url",
            action_attr.url_path,
        )
        action_kwargs.update(
            queryset=resource_class.get_model_queryset(),
            serializer_class=action_view.get_export_create_serializer_class(),
            filter_backends=filter_backends,
            filterset_class=getattr(resource_class, "filterset_class", None),
            ordering=action_view.export_ordering,
            ordering_fields=action_view.export_ordering_fields,
            permission_classes=(
                action_view.export_permission_classes
                or default_permission_classes
            ),
            throttle_classes=(
                action_view.export_throttle_classes or default_throttle_classes
            ),
            throttle_scope=action_view.export_throttle_scope,
        )
        cls.set_up_export_action_api_specs(
            action_name=action_name,
            action_view=action_view,
        )

    @classmethod
    def set_up_export_action_api_specs(
        cls,
        action_name: str,
        action_view: "ExportStartActionMixin",
    ) -> None:
        """Correct specs of drf-spectacular if it is installed."""
        with contextlib.suppress(ImportError):
            from drf_spectacular import utils

            utils.extend_schema_view(
                **{
                    action_name: utils.extend_schema(
                        description=action_view.export_open_api_description,
                        filters=True,
                        responses={
                            drf_status.HTTP_201_CREATED: action_view.get_export_detail_serializer_class(),  # noqa: E501
                        },
                    ),
                },
            )(cls)

    def get_queryset(self) -> QuerySet:
        """Return export model queryset on export action.

        For better openapi support and consistency.

        """
        if self.is_export_action:
            return self.resource_class.get_model_queryset()  # pragma: no cover
        return super().get_queryset()  # type: ignore[misc]

    def get_export_detail_serializer_class(
        self,
    ) -> type[serializers.ExportJobSerializer]:
        """Get serializer which will be used show details of export job."""
        return self.export_detail_serializer_class

    def get_export_create_serializer_class(
        self,
    ) -> type[drf_serializers.Serializer]:
        """Get serializer which will be used to start export job."""
        return serializers.get_create_export_job_serializer(
            self.resource_class,
        )

    def get_export_resource_kwargs(self) -> dict[str, typing.Any]:
        """Provide extra arguments to resource class."""
        return {}

    def get_serializer(self, *args, **kwargs) -> drf_serializers.Serializer:
        """Provide resource kwargs to serializer class."""
        if self.is_export_action:
            kwargs.setdefault(
                "resource_kwargs",
                self.get_export_resource_kwargs(),
            )
        return super().get_serializer(*args, **kwargs)  # type: ignore[misc]

    def start_export(
        self,
        request: drf_request.Request,
    ) -> drf_response.Response:
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
        return drf_response.Response(
            data=self.get_export_detail_serializer_class()(
                instance=export_job,
            ).data,
            status=drf_status.HTTP_201_CREATED,
        )
