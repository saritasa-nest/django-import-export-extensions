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
        path=reverse("admin:fake_app_artist_import"),
    )
    assert import_response.status_code == status.HTTP_200_OK

    # Start import job using admin panel
    start_import_job_response = client.post(
        path=reverse("admin:fake_app_artist_import"),
        data={
            "import_file": uploaded_file,
            "input_format": 0,  # Choose CSV format
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


@pytest.mark.usefixtures("existing_artist")
def test_import_admin_has_same_formats(
    client: Client,
    superuser: User,
    artist_import_job: ImportJob,
):
    """Ensure input formats on import forms are the same.

    Ensure Import forms on import and on import result pages
    fetch format choices from the same source.

    """
    client.force_login(superuser)
    artist_import_job.import_status = ImportJob.ImportStatus.IMPORTED
    artist_import_job.save()
    import_response = client.get(
        path=reverse("admin:fake_app_artist_import"),
    )
    import_response_result = client.get(
        path=reverse(
            "admin:fake_app_artist_import_job_results",
            kwargs={"job_id": artist_import_job.id},
        ),
    )
    import_response_form = import_response.context_data["form"]
    import_response_result_form = import_response_result.context_data["import_form"]
    assert (
        import_response_form.fields["input_format"].choices ==
        import_response_result_form.fields["input_format"].choices
    )
