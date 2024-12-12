===============
Getting started
===============

``django-import-export-extensions`` is based on ``django-import-export`` package,
so it follows a similar workflow and interfaces. If you are already familiar with the original package,
you can refer to the :ref:`Migrate from original django-import-export package<Migrate from original \`django-import-export\` package>`
section to start using background import/export.

You can also consult the `django-import-export documentation <https://django-import-export.readthedocs.io/en/latest/index.html>`_
to learn how to work with import and export features.

There are simple examples to quickly get import/export functionality.

Django Model for tests
----------------------

There is simple django model from test app that we gonna use in the examples above.

.. code-block:: python

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

Resources
---------

The resource class is a core of import/export. It is similar to Django forms but provides methods
for converting data between files and objects.

``django-import-export-extensions`` provides two key classes: ``CeleryResource`` and ``CeleryModelResource``. Below is an example of a simple model resource:

.. code-block:: python

    from import_export_extensions.resources import CeleryModelResource


    class BandResource(CeleryModelResource):
        """Resource for `Band` model."""

        class Meta:
            model = Band
            fields = [
                "id",
                "title",
            ]

This resource class allows you to import/export data just like the original package. However, to
perform imports/exports in the background, you need to create ``ImportJob`` and ``ExportJob`` objects.

The resource classes have been modified to interact with Celery, but the overall workflow
remains the same. For more details, refer to the
`Resources <https://django-import-export.readthedocs.io/en/latest/api_resources.html>`_
and
`Import data workflow <https://django-import-export.readthedocs.io/en/latest/import_workflow.html#>`_
sections of the base package documentation.

Job Models
----------

The package provides the ``ImportJob`` and ``ExportJob`` models, which are at the core of background
import/export functionality. These models store the parameters and results of the import/export process.
Once you create an instance of one of these classes, the Celery task is triggered,
and the import/export process begins.

Example of creation:

.. code-block:: python

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

These models are also registered in the Django Admin, allowing you to view all information about
the created jobs directly from the admin interface.

Admin models
------------

To perform import/export operations using Celery through Django Admin,
use the ``CeleryImportExportMixin`` in your admin model and set the ``resource_classes`` class attribute.

.. code-block:: python

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

There are also the ``CeleryImportAdminMixin`` and ``CeleryExportAdminMixin`` mixins available
if you need to perform only one operation (import or export) in the admin. All of these mixins add
a ``status page``, where you can monitor the progress of the import/export process:

.. figure:: _static/images/export-status.png

   A screenshot of Django Admin export status page

Import/Export API
-----------------

The ``api.views.ExportJobViewSet`` and ``api.views.ImportJobViewSet`` are provided to create
the corresponding viewsets for the resource.

.. code-block:: python

    from import_export_extensions.api import views
    from . import resources


    class BandExportViewSet(views.ExportJobViewSet):
        """Simple ViewSet for exporting `Band` model."""
        resource_class = resources.BandResource


    class BandImportViewSet(views.ImportJobViewSet):
        """Simple ViewSet for importing `Band` model."""
        resource_class = resources.BandResource

These viewsets provide the following actions to manage ``ImportJob``/``ExportJob`` objects:

* ``list`` - Returns a list of jobs for the ``resource_class`` set in ViewSet
* ``retrieve`` - Returns details of a job based on the provided ID
* ``start`` - Creates a job object and starts the import/export process
* ``cancel`` - Stops the import/export process and sets the job's status to ``CANCELLED``.
* ``confirm`` - Confirms the import after the parse stage. This action is available only in ``ImportJobViewSet``.

Additionally, there is ``drf_spectacular`` integration. If you have this package configured,
the OpenAPI specification will be available.

.. figure:: _static/images/bands-openapi.png

   A screenshot of the generated OpenAPI specification
