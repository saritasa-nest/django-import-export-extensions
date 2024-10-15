import sys

from rest_framework import viewsets

import pytest
import pytest_mock

from import_export_extensions.api.views import (
    ExportJobViewSet,
    ImportJobViewSet,
)
from test_project.fake_app.resources import SimpleArtistResource


@pytest.mark.parametrize(
    argnames="viewset_class",
    argvalues=[
        ExportJobViewSet,
        ImportJobViewSet,
    ],
)
def test_new_viewset_class(
    viewset_class: type[viewsets.GenericViewSet],
    mocker: pytest_mock.MockerFixture,
):
    """Check that if drf_spectacular is not set it will not raise an error."""
    mocker.patch.dict(sys.modules, {"drf_spectacular.utils": None})

    class TestViewSet(viewset_class):
        resource_class = SimpleArtistResource

    assert TestViewSet is not None
