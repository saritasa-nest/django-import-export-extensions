# Getting started

`django-import-export-extensions` is based on `django-import-export`
package, so it follows a similar workflow and interfaces. If you are
already familiar with the original package, you can refer to the
[Migrate from original django-import-export package](migrate_from_original_import_export.md)
section to start using background import/export.

You can also consult the
[django-import-export documentation](https://django-import-export.readthedocs.io/en/latest/index.html)
to learn how to work with import and export features.

There are simple examples to quickly get import/export functionality.

## Django Model for tests

There is simple Django model from test app that we gonna use in the
examples above.

``` python
from django.db import models


class Band(models.Model):

    title = models.CharField(
        max_length=100,
    )

    class Meta:
        verbose_name = _("Band")
        verbose_name_plural = _("Bands")

    def __str__(self) -> str:
        return self.title
```

## Resources

The resource class is a core of import/export. It is similar to Django
forms but provides methods for converting data between files and
objects.

`django-import-export-extensions` provides two key classes:
`CeleryResource` and `CeleryModelResource`. Below is an example of a
simple model resource:

``` python
from import_export_extensions.resources import CeleryModelResource


class BandResource(CeleryModelResource):
    """Resource for `Band` model."""

    class Meta:
        model = Band
        fields = [
            "id",
            "title",
        ]
```

This resource class allows you to import/export data just like the
original package. However, to perform imports/exports in the background,
you need to create `ImportJob` and `ExportJob` objects.

The resource classes have been modified to interact with Celery, but the
overall workflow remains the same. For more details, refer to the
[Resources](https://django-import-export.readthedocs.io/en/latest/api_resources.html)
and [Import data workflow](https://django-import-export.readthedocs.io/en/latest/import_workflow.html#)
sections of the base package documentation.

## Job Models

The package provides the `ImportJob` and `ExportJob` models, which are
at the core of background import/export functionality. These models
store the parameters and results of the import/export process. Once you
create an instance of one of these classes, the Celery task is
triggered, and the import/export process begins.

Example of creation:

``` python
from import_export_extensions import models
from . import resources

file_format_path = "import_export.formats.base_formats.CSV"
import_file = "files/import_file.csv"

# Start import job
import_job = models.ImportJob.objects.create(
    resource_path=resources.BandResource.class_path,
    data_file=import_file,
    resource_kwargs={},
)

# Start export job
export_job = models.ExportJob.objects.create(
    resource_path=resources.BandResource.class_path,
    file_format_path=file_format_path,
    resource_kwargs={}
)

print(import_job.import_status, export_job.export_status)  # CREATED CREATED
```

These models are also registered in the Django Admin, allowing you to
view all information about the created jobs directly from the admin
interface.

## Signals

The package provides signals `export_job_failed` and
`import_job_failed`. You can use them to handle errors that
happened during job.

Example

```python title="signals.py"
import logging

from django import dispatch

from import_export_extensions.models.core import BaseJob
from import_export_extensions.signals import (
    export_job_failed,
    import_job_failed,
)


@dispatch.receiver(export_job_failed)
@dispatch.receiver(import_job_failed)
def job_error_hook(
    sender,
    instance: BaseJob,
    error_message: str,
    traceback: str,
    exception: Exception | None,
    **kwargs,
):
    """Present an example of job error hook."""
    logging.getLogger(__file__).warning(f"{instance}, {error_message}")
```

## Admin models

To perform import/export operations using Celery through Django Admin,
use the `CeleryImportExportMixin` in your admin model and set the
`resource_classes` class attribute.

```python title="admin.py"
from import_export_extensions.admin import CeleryImportExportMixin
from . import resources
from . import models


@admin.register(models.Band)
class BandAdmin(CeleryImportExportMixin, admin.ModelAdmin):
    """Admin for `Band` model with import export functionality."""
    list_display = (
        "title",
    )
    resource_classes = [resources.BandResource]
```

There are also the `CeleryImportAdminMixin` and `CeleryExportAdminMixin`
mixins available if you need to perform only one operation (import or
export) in the admin. All of these mixins add a `status page`, where you
can monitor the progress of the import/export process:

![A screenshot of Django Admin export status page](_static/images/export-status.png)

## Import/Export API

The `api.views.ExportJobViewSet` and `api.views.ImportJobViewSet` are
provided to create the corresponding viewsets for the resource.

```python title="views.py"
from import_export_extensions.api import views
from . import resources


class BandExportViewSet(views.ExportJobViewSet):
    """Simple ViewSet for exporting `Band` model."""
    resource_class = resources.BandResource


class BandImportViewSet(views.ImportJobViewSet):
    """Simple ViewSet for importing `Band` model."""
    resource_class = resources.BandResource
```

These viewsets provide the following actions to manage
`ImportJob`/`ExportJob` objects:

- `list` - Returns a list of jobs for the `resource_class` set in
    ViewSet
- `retrieve` - Returns details of a job based on the provided ID
- `start` - Creates a job object and starts the import/export process
- `cancel` - Stops the import/export process and sets the job\'s
    status to `CANCELLED`.
- `confirm` - Confirms the import after the parse stage. This action
    is available only in `ImportJobViewSet`.

Additionally, there is `drf_spectacular` integration. If you have this
package configured, the OpenAPI specification will be available.

![A screenshot of the generated OpenAPI specification](_static/images/bands-openapi.png)

## Import/Export API actions mixins

Alternatively you can use `api.mixins.ExportStartActionMixin` and
`api.mixins.ImportStartActionMixin` to add to your current viewsets
ability to create import/export jobs. You would also need to use
`api.views.BaseExportJobViewSet` or `BaseExportJobForUsersViewSet` and
`api.views.BaseImportJobViewSet` or `BaseImportJobForUsersViewSet` to
setup endpoints to be able to:

- `list` - Returns a list of jobs for the `resource_class` set in
    ViewSet.
- `retrieve` - Returns details of a job based on the provided ID.
- `cancel` - Stops the import/export process and sets the job\'s
    status to `CANCELLED`.
- `confirm` - Confirms the import after the parse stage. This action
    is available only in import jobs.

![A screenshot of the generated OpenAPI specification](_static/images/action-bands-openapi.png)
