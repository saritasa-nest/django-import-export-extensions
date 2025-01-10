class LimitQuerySetToCurrentUserMixin:
    """Make queryset to return only current user jobs."""

    def get_queryset(self):
        """Return user's jobs."""
        if self.action == "start":
            # To make it consistent and for better support of drf-spectacular
            return super().get_queryset()
        return (
            super()
            .get_queryset()
            .filter(created_by_id=getattr(self.request.user, "pk", None))
        )
