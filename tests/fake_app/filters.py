from django_filters import rest_framework as filters

from tests.fake_app.models import Artist


class ArtistFilterSet(filters.FilterSet):
    """FilterSet for Artist resource."""

    class Meta:
        model = Artist
        fields = [
            "id",
            "name",
        ]
