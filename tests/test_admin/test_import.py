"""There are kind a functional tests for import using Django Admin."""
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.client import Client
from django.urls import reverse

from rest_framework import status

import pytest

from import_export_extensions.models import ImportJob


@pytest.mark.usefixtures("existing_artist")
@pytest.mark.django_db(transaction=True)
def test_import_using_admin_model(
    client: Client,
    superuser: User,
    uploaded_file: SimpleUploadedFile,
):
    """Test entire importing process using Django Admin.

    There is following workflow:
        1. Go to Artist Import page
        2. Start Import Job with chosen file
        3. Redirect to the import job parsing result page through
           the status page
        4. Confirm import
        5. Redirect to the import job importing page through the status page

    """
    client.force_login(superuser)

    # Go to import page in admin panel
    import_response = client.get(
        path=reverse("admin:fake_app_artist_celery_import"),
    )
    assert import_response.status_code == status.HTTP_200_OK

    # Start import job using admin panel
    start_import_job_response = client.post(
        path=reverse("admin:fake_app_artist_celery_import"),
        data={
            "import_file": uploaded_file,
        },
    )
    assert start_import_job_response.status_code == status.HTTP_302_FOUND

    # Go to import job status page
    # Ensure there is another one redirect because import job finished
    status_page_response = client.get(path=start_import_job_response.url)
    assert status_page_response.status_code == status.HTTP_302_FOUND

    assert ImportJob.objects.exists()

    import_job = ImportJob.objects.first()

    # Go to results page
    result_page_get_response = client.get(status_page_response.url)
    assert result_page_get_response.status_code == status.HTTP_200_OK

    # Confirm import on result page
    confirm_response = client.post(
        path=status_page_response.url, data={"confirm": "Confirm import"},
    )
    assert confirm_response.status_code == status.HTTP_302_FOUND

    # Ensure import job finished and redirected to result page
    import_status_response = client.get(path=confirm_response.url)
    assert import_status_response.status_code == status.HTTP_302_FOUND

    result_response = client.get(path=import_status_response.url)

    assert result_response.status_code == status.HTTP_200_OK

    import_job.refresh_from_db()
    assert import_job.import_status == ImportJob.ImportStatus.IMPORTED
