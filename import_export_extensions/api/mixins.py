class LimitQuerySetToCurrentUserMixin:
    """Make queryset to return only current user jobs."""

    def get_queryset(self):
        """Return user's jobs."""
        return (
            super()
            .get_queryset()
            .filter(created_by_id=getattr(self.request.user, "pk", None))
        )
