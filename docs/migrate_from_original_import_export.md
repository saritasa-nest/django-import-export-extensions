# Migrate from original django-import-export package

If you're already using `django-import-export` and want to take
advantage of `django-import-export-extensions` for background
import/export, the transition is simple. First, install the package by
following the the installation guide
[Installation and configuration](./installation.md).
Then, all you need to do is update the base classes for your resource and admin models.

## Migrate resources

To enable import/export via Celery, simply replace the base resource
classes from the original package with `CeleryResource` or
`CeleryModelResource` from `django-import-export-extensions`:

```diff
- from import_export import resources
+ from import_export_extensions import resources

class SimpleResource(
-     resources.Resource,
+     resources.CeleryResource,
):
    """Simple resource."""


class BookResource(
-    resources.ModelResource,
+    resources.CeleryModelResource,
):
    """Resource class for `Book` model."""

    class Meta:
        model = Book
```

## Migrate admin models

Then you also need to change admin mixins to use celery import/export
via Django Admin:

```diff

- from import_export.admin import ImportExportModelAdmin
+ from import_export_extensions.admin import CeleryImportExportMixin

from . import resources

class BookAdmin(
-    ImportExportModelAdmin,
+    CeleryImportExportMixin,
+    admin.ModelAdmin,
):
    """Resource class for `Book` model."""

    resource_classes = (
        resources.BookResource,
    )
```

If you only need import (or export) functionality, you can use the
`CeleryImportAdminMixin` (or `CeleryExportAdminMixin`) instead of the
`CeleryImportExportMixin`.

## Migrate custom import/export

Background import/export is implemented using the `ImportJob` and
`ExportJob` models. As a result, calling the simple `resource.export()`
will not trigger a Celery task --- it behaves exactly like the original
`Resource.export()` method. To initiate background import/export, you
need to create instances of the import/export job:

```python
>>> from .resources import BandResource
>>> from import_export.formats import base_formats
>>> from import_export_extensions.models import ExportJob
>>> file_format = base_formats.CSV
>>> file_format_path = f"{file_format.__module__}.{file_format.__name__}"
>>> export_job = ExportJob.objects.create(
        resource_path=BandResource.class_path,
        file_format_path=file_format_path
    )
>>> export_job.export_status
'CREATED'
```

You can check the current status of the job using the `export_status`
(or `import_status`) property of the model. Additionally, the `progress`
property provides information about the total number of rows and the
number of rows that have been completed.

```python
>>> export_job.refresh_from_db()
>>> export_job.export_status
'EXPORTING'
>>> export_job.progress
{'state': 'EXPORTING', 'info': {'current': 53, 'total': 100}}
>>> export_job.refresh_from_db()
>>> export_job.export_status
'EXPORTED'
>>> export_job.data_file.path
'../media/import_export_extensions/export/3dfb7510-5593-4dc6-9d7d-bbd907cd3eb6/Artists-2020-02-22.csv'
```

## Other configuration

You may need to configure
[MEDIA_URL](https://docs.djangoproject.com/en/stable/ref/settings/#media-url)
in your project settings, otherwise you may see a 404 error when
attempting to download exported files.
