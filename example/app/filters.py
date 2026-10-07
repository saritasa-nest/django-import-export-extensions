from django_filters import rest_framework as filters

from . import models


class ArtistFilterSet(filters.FilterSet):
    """FilterSet for Artist resource."""

    class Meta:
        model = models.Artist
        fields = {
            "id": (
                "exact",
                "in",
            ),
            "name": (
                "exact",
                "in",
            ),
        }


class ArtistM2MFilterSet(filters.FilterSet):
    """FilterSet for Artist resource for m2m export."""

    class Meta:
        model = models.Artist
        fields = {
            "id": (
                "exact",
                "in",
            ),
            "name": (
                "exact",
                "in",
            ),
            "instrument": (
                "exact",
                "in",
            ),
        }
