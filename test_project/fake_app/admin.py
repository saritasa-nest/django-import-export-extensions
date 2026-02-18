from django.contrib import admin

from import_export_extensions.admin import CeleryImportExportMixin

from . import models, resources


@admin.register(models.Artist)
class ArtistAdmin(CeleryImportExportMixin, admin.ModelAdmin):
    """Simple Artist admin model for tests."""

    list_display = (
        "name",
        "instrument",
    )
    list_filter = (
        "instrument__title",
    )
    search_fields = (
        "instrument__title__icontains",
        "name",
        # `@name`, `^name`, `=name` are about one model field but thanks for
        # first symbol they apply difference lookups in search.
        # These ones are used to check that type of search filter
        # must be only one for a model field in admin class.
        # They are not required, it's just for testing
        # https://github.com/django/django/blob/d6925f0d6beb3c08ae24bdb8fd83ddb13d1756e4/django/contrib/admin/options.py#L1138
        "@name",
        "^name",
        "=name",
    )
    resource_classes = (
        resources.ArtistResourceWithM2M,
        resources.SimpleArtistResource,
    )


@admin.register(models.Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    """Simple Instrument admin model for tests."""

    list_display = (
        "title",
    )


@admin.register(models.Band)
class BandAdmin(CeleryImportExportMixin, admin.ModelAdmin):
    """Band admin model for tests."""

    list_display = (
        "id",
        "title",
    )
    search_fields = (
        "id",
        "title",
    )
    resource_classes = (
        resources.BandResourceWithM2M,
    )


@admin.register(models.Membership)
class MembershipAdmin(admin.ModelAdmin):
    """Membership admin model for tests."""

    list_display = (
        "id",
        "date_joined",
    )
