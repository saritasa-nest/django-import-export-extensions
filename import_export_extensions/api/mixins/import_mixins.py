import contextlib
import typing

from rest_framework import (
    decorators,
    request,
    response,
    status,
)

from ... import resources
from .. import serializers


class ImportStartActionMixin:
    """Mixin which adds start import action."""

    resource_class: type[resources.CeleryModelResource]
    import_action = "start_import_action"
    import_action_name = "import"
    import_action_url = "import"
    import_detail_serializer_class = serializers.ImportJobSerializer
    import_open_api_description = (
        "This endpoint creates import job and starts it. "
        "To monitor progress use detail endpoint for jobs to fetch state of "
        "job. Once it's status is `PARSED`, you can confirm import and data "
        "should start importing. When status `INPUT_ERROR` or `PARSE_ERROR` "
        "it means data failed validations and can't be imported. "
        "When status is `IMPORTED`, it means data is in system and "
        "job is completed."
    )

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        # Skip if it is has no resource_class specified
        if not hasattr(cls, "resource_class"):
            return

        def start_import_action(
            self: "ImportStartActionMixin",
            request: request.Request,
            *args,
            **kwargs,
        ) -> response.Response:
            return self.start_import(request)

        setattr(cls, cls.import_action, start_import_action)
        decorators.action(
            methods=["POST"],
            url_name=cls.import_action_name,
            url_path=cls.import_action_url,
            detail=False,
            queryset=cls.resource_class.get_model_queryset(),
            serializer_class=cls().get_import_create_serializer_class(),
        )(getattr(cls, cls.import_action))
        # Correct specs of drf-spectacular if it is installed
        with contextlib.suppress(ImportError):
            from drf_spectacular import utils

            utils.extend_schema_view(
                **{
                    cls.import_action: utils.extend_schema(
                        description=cls.import_open_api_description,
                        filters=True,
                        responses={
                            status.HTTP_201_CREATED: cls().get_import_detail_serializer_class(),  # noqa: E501
                        },
                    ),
                },
            )(cls)

    def get_queryset(self):
        """Return import model queryset on import action.

        For better openapi support and consistency.

        """
        if self.action == self.import_action:
            return self.resource_class.get_model_queryset()  # pragma: no cover
        return super().get_queryset()

    def get_import_detail_serializer_class(self):
        """Get serializer which will be used show details of import job."""
        return self.import_detail_serializer_class

    def get_import_create_serializer_class(self):
        """Get serializer which will be used to start import job."""
        return serializers.get_create_import_job_serializer(
            self.resource_class,
        )

    def get_import_resource_kwargs(self) -> dict[str, typing.Any]:
        """Provide extra arguments to resource class."""
        return {}

    def get_serializer(self, *args, **kwargs):
        """Provide resource kwargs to serializer class."""
        if self.action == self.import_action:
            kwargs.setdefault(
                "resource_kwargs",
                self.get_import_resource_kwargs(),
            )
        return super().get_serializer(*args, **kwargs)

    def start_import(self, request: request.Request) -> response.Response:
        """Validate request data and start ImportJob."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        import_job = serializer.save()

        return response.Response(
            data=self.get_import_detail_serializer_class()(
                instance=import_job,
            ).data,
            status=status.HTTP_201_CREATED,
        )
