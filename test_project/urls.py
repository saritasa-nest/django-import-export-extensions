from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from rest_framework.routers import DefaultRouter

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from import_export_extensions import api

from .fake_app.api import views

ie_router = DefaultRouter()
ie_router.register(
    "export-artist",
    views.ArtistExportViewSet,
    basename="export-artist",
)
ie_router.register(
    "export-jobs",
    api.BaseExportJobForUserViewSet,
    basename="export-jobs",
)
ie_router.register(
    "import-jobs",
    api.BaseImportJobForUserViewSet,
    basename="import-jobs",
)
ie_router.register(
    "import-artist",
    views.ArtistImportViewSet,
    basename="import-artist",
)
ie_router.register(
    "artists",
    views.ArtistViewSet,
    basename="artists",
)

urlpatterns = [re_path("^admin/", admin.site.urls), *ie_router.urls]


# for serving uploaded files on dev environment with django
if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        path(
            "api/schema/",
            SpectacularAPIView.as_view(),
            name="schema",
        ),
        path(
            "api/schema/swagger-ui/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
        path("__debug__/", include(debug_toolbar.urls)),
    ]

    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT,
    )
