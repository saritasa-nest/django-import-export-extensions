from django.apps import AppConfig


class IOExtensionsAppConfig(AppConfig):
    """Fake app config."""

    name = "test_project.fake_app"
    verbose_name = "Import Export Fake App"

    def ready(self):
        # Import to connect signals.
        from . import signals  # noqa: F401
