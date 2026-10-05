from django.apps import AppConfig


class IOExtensionsAppConfig(AppConfig):
    """Fake app config."""

    name = "example.app"
    verbose_name = "Import Export Fake App"

    def ready(self) -> None:
        # Import to connect signals.
        from . import signals  # noqa: F401
