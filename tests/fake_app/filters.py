from django_filters import FilterSet

from tests.fake_app.models import Artist


class ArtistFilterSet(FilterSet):
    """FilterSet for Artist resource."""

    class Meta:
        model = Artist
        fields = [
            "id",
            "name",
        ]
