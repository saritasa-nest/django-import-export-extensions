from django.contrib.auth.models import User
from django.test.client import Client
from django.urls import reverse

from rest_framework import status


def test_changelist_view_permission_context(
    client: Client,
    superuser: User,
):
    """Make sure changelist view has property to show import/export buttons."""
    client.force_login(superuser)

    response = client.get(
        path=reverse("admin:fake_app_artist_changelist"),
    )
    assert response.status_code == status.HTTP_200_OK
    context = response.context
    assert context["has_export_permission"]
    assert context["has_import_permission"]
