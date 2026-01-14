from django.db.models import QuerySet


class LimitQuerySetToCurrentUserMixin:
    """Make queryset to return only current user jobs."""

    def get_queryset(self) -> QuerySet:
        """Return user's jobs."""
        if self.action in (
            getattr(self, "import_action", ""),
            getattr(self, "export_action", ""),
        ):
            # To make it consistent and for better support of drf-spectacular
            return (
                super().get_queryset()  # type: ignore[misc]
            )  # pragma: no cover
        return (
            super()  # type: ignore[misc]
            .get_queryset()
            .filter(created_by_id=getattr(self.request.user, "pk", None))
        )
