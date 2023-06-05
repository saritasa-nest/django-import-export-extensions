from django.contrib import admin

from import_export_extensions.admin import CeleryImportExportMixin

from .models import Artist, Band, Instrument, Membership
from .resources import ArtistResourceWithM2M, SimpleArtistResource


@admin.register(Artist)
class ArtistAdmin(CeleryImportExportMixin, admin.ModelAdmin):
    """Simple Artist admin model for tests."""
    list_display = (
        "name",
        "instrument",
    )
    resource_classes = [SimpleArtistResource, ArtistResourceWithM2M]


@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    """Simple Instrument admin model for tests."""
    list_display = ("title",)


@admin.register(Band)
class BandAdmin(admin.ModelAdmin):
    """Band admin model for tests."""
    list_display = (
        "id",
        "title",
    )
    search_fields = (
        "id",
        "title",
    )


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    """Membership admin model for tests."""
    list_display = (
        "id",
        "date_joined",
    )
