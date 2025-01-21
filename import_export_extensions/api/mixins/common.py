class LimitQuerySetToCurrentUserMixin:
    """Make queryset to return only current user jobs."""

    def get_queryset(self):
        """Return user's jobs."""
        if self.action in (
            getattr(self, "import_action", ""),
            getattr(self, "export_action", ""),
        ):
            # To make it consistent and for better support of drf-spectacular
            return super().get_queryset()  # pragma: no cover
        return (
            super()
            .get_queryset()
            .filter(created_by_id=getattr(self.request.user, "pk", None))
        )
