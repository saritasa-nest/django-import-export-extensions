# -*- coding: utf-8 -*

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, re_path

from rest_framework.routers import DefaultRouter

from drf_spectacular.views import SpectacularSwaggerView

from .fake_app.api import views

ie_router = DefaultRouter()
ie_router.register(
    "export-artist",
    views.ArtistExportViewSet,
    basename="export-artist",
)
ie_router.register(
    "import-artist",
    views.ArtistImportViewSet,
    basename="import-artist",
)

urlpatterns = [
    re_path(r"^admin/", admin.site.urls),
] + ie_router.urls


# for serving uploaded files on dev environment with django
if settings.DEBUG:

    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT,
    )
    urlpatterns += [
        path(
            "api/schema/swagger-ui/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
    ]
