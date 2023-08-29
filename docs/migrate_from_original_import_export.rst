====================================================
Migrate from original `django-import-export` package
====================================================

If you are already using ``django-import-export`` and want to use ``django-import-export-extensions``,
you can easily switch to it and get the benefits of background import/exporting.
First of all, install the package according to :ref:`the instruction<Installation and configuration>`.
And now, all you need is to change base classes of resources and admin models.

Migrate resources
-----------------

To use resources that provides import/export via Celery just change base resource classes from
original package to ``CeleryResource`` / ``CeleryModelResource`` from ``django-import-export-extensions``:

.. code-block:: diff
    :emphasize-lines: 2,6,13

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

Migrate admin models
--------------------

Then you also need to change admin mixins to use celery import/export via Django Admin:

.. code-block:: diff
    :emphasize-lines: 4,10,11

    from django.contrib import admin

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


If you only need import (or export) functionality, you can use ``CeleryImportAdminMixin``
(``CeleryExportAdminMixin``) instead of ``CeleryImportExportMixin``.

Migrate custom import/export
----------------------------

Background import/export is implemented based on ``ImportJob``/``ExportJob`` models. So simple
``resource.export()`` won't trigger a celery task, it works exactly the same as the original
``Resource.export()`` method. To start background import/export, you need to create objects of
import/export job:

.. code-block:: python
    :linenos:

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

Using the ``export_status`` (``import_status``) property of the model, you can check the current status of the job.
There is also a ``progress`` property that returns information about the total number and number of completed rows.

.. code-block:: python
    :linenos:
    :emphasize-lines: 2,4

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
