import sys

import pytest
import pytest_mock
from rest_framework import viewsets

from example.app import resources
from import_export_extensions.api import views


@pytest.mark.parametrize(
    argnames="viewset_class",
    argvalues=[
        views.ExportJobViewSet,
        views.ImportJobViewSet,
    ],
)
def test_new_viewset_class(
    viewset_class: type[viewsets.GenericViewSet],
    mocker: pytest_mock.MockerFixture,
):
    """Check that if drf_spectacular is not set it will not raise an error."""
    mocker.patch.dict(sys.modules, {"drf_spectacular.utils": None})

    class TestViewSet(viewset_class):
        resource_class = resources.SimpleArtistResource

    assert TestViewSet is not None
