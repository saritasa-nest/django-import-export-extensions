import django.test
from django.db.models import Q

import pytest

from import_export_extensions import utils

AWS_STORAGE_BUCKET_NAME = "test-bucket-name"


@pytest.mark.parametrize(
    argnames=["file_url", "expected_mime_type"],
    argvalues=[
        pytest.param(
            "dir/subdir/file.invalid_extension",
            "application/octet-stream",
            id="File extension not in setting.MIME_TYPES_MAP",
        ),
        pytest.param(
            "dir/subdir/file.json",
            "application/json",
            id="File extension in settings.MIME_TYPES_MAP",
        ),
        pytest.param(
            "http://testdownload.org/file.csv?width=10",
            "text/csv",
            id="File url with GET params",
        ),
    ],
)
def test_get_mime_type_by_file_url(
    file_url: str,
    expected_mime_type: str,
):
    """Check that correct mime type is returned."""
    assert utils.get_mime_type_by_file_url(file_url) == expected_mime_type


def test_clear_q_filter():
    """Check that filter is cleaned correctly."""
    value = "Hello world"
    attribute_name = "title"
    expected_q_filter = Q(title__iregex=r"^Hello\s+world$")

    assert utils.get_clear_q_filter(value, attribute_name) == expected_q_filter


@django.test.override_settings(
    AWS_STORAGE_BUCKET_NAME=AWS_STORAGE_BUCKET_NAME,
)
@pytest.mark.parametrize(
    argnames=["file_url", "expected_file_url"],
    argvalues=[
        pytest.param(
            "http://localhost:8000/media/dir/file.csv",
            "dir/file.csv",
            id="File from media",
        ),
        pytest.param(
            f"http://s3.region.com/{AWS_STORAGE_BUCKET_NAME}/dir/file.csv",
            "dir/file.csv",
            id="File from s3 bucket",
        ),
        pytest.param(
            f"http://{AWS_STORAGE_BUCKET_NAME}.s3.region.com/dir/file.csv",
            "dir/file.csv",
            id=(
                "File from s3 bucket if using virtual addressing style:"
                "https://docs.aws.amazon.com/AmazonS3/latest/userguide/VirtualHosting.html"
            ),
        ),
    ],
)
def test_url_to_internal_value(
    file_url: str,
    expected_file_url: str,
):
    """Check that file url is converted correctly."""
    assert utils.url_to_internal_value(file_url) == expected_file_url
