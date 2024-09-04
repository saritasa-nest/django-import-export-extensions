"""There are kind a functional tests for export using Django Admin."""

from django.contrib.auth.models import User
from django.test.client import Client
from django.urls import reverse

from rest_framework import status

import pytest

from import_export_extensions.models import ExportJob


@pytest.mark.usefixtures("existing_artist")
@pytest.mark.django_db(transaction=True)
def test_export_using_admin_model(client: Client, superuser: User):
    """Test entire exporting process using Django Admin.

    There is following workflow:
        1. Go to Artist Export page
        2. Start Export Job with chosen file format (csv)
        3. Redirect to export job result page through the status page

    """
    client.force_login(superuser)

    # Make get request to admin export page
    export_get_response = client.get(
        path=reverse("admin:fake_app_artist_export"),
    )
    assert export_get_response.status_code == status.HTTP_200_OK

    # Start export job using admin panel
    start_export_response = client.post(
        path=reverse("admin:fake_app_artist_export"),
        data={
            "file_format": 0,
        },
    )
    assert start_export_response.status_code == status.HTTP_302_FOUND

    # Go to redirected page after export is finished
    status_response = client.get(start_export_response.url)
    assert status_response.status_code == status.HTTP_302_FOUND

    result_response = client.get(status_response.url)
    assert result_response.status_code == status.HTTP_200_OK

    assert ExportJob.objects.exists()
    export_job = ExportJob.objects.first()
    assert export_job.export_status == ExportJob.ExportStatus.EXPORTED
