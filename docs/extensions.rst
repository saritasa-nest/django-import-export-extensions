==========
Extensions
==========

This package is simply an extension of the original ``django-import-export``, so if you want
to know more about the import/export process and advanced resource utilization, you should refer to
`the official django-import-export documentation <https://django-import-export.readthedocs.io/en/latest/index.html>`_.

This section describes the features that are added by this package.

--------------------------
ImportJob/ExportJob models
--------------------------

The ``django-import-export-extensions`` provides ``ImportJob`` and ``ExportJob`` models to store all the information
about the import/export process. In addition, these models participate in the background import/export process.

Job models are already registered in Django Admin and have custom forms that allow to show
all current job information including import/export status.

.. figure:: _static/images/import-job-admin.png

   Example of custom form for ImportJob details in Django Admin

``ImportJob``/``ExportJob`` models contain useful properties and methods for managing
the import/export process. To learn more, see the :ref:`Models API documentation<Models>`.

-------------------
Celery admin mixins
-------------------

The mixins for admin models have been rewritten completely, although they inherit from the base mixins
``mixins.BaseImportMixin``, ``mixins.BaseExportMixin`` and ``admin.ImportExportMixinBase``.
The new celery admin mixins add new pages to display import/export status, and use custom
templates for the status and results pages.

Now after starting the import/export, you will first be redirected to the status page and then,
after the import/export is complete, to the results page.

.. figure:: _static/images/export-status.png

   A screenshot of Djagno Admin export status page

--------
ViewSets
--------

There are ``ImportJobViewSet`` and ``ExportJobViewSet`` view sets that make it easy
to implement import/export via API. Just create custom class with ``resource_class`` attribute:

**api/views.py**

.. code-block:: python

    from import_export_extensions.api import views as import_export_views
    from . import resources


    class BandImportViewSet(import_export_views.ImportJobViewSet):
        resource_class = resources.BandResource


    class BandExportViewSet(import_export_views.ExportJobViewSet):
        resource_class = resources.BandResource


**urls.py**

.. code-block:: python

    from rest_framework.routers import DefaultRouter
    from .api import views

    band_import_export_router = DefaultRouter()
    band_import_export_router.register(
        "import-band",
        views.BandImportViewSet,
        basename="import-band",
    )
    band_import_export_router.register(
        "export-band",
        views.BandExportViewSet,
        basename="export-band",
    )

    urlpatterns = band_import_export_router.urls

By default, all import/export jobs for the set ``resource_class`` will be available,
but you can override ``get_queryset`` method to change it. You can also override
``get_resource_kwargs`` method to provide some values in resource class (for ``start`` action).

These view sets provide all methods required for entire import/export workflow: start, details,
confirm, cancel and list actions. There is also `drf-spectacular <https://github.com/tfranzel/drf-spectacular>`_
integrations, you can see generated openapi UI for these view sets
(``drf-spectacular`` must be installed in your project):

.. figure:: _static/images/bands-openapi.png

-------
Filters
-------

``CeleryResource`` and ``CeleryModelResource`` also support `django-filter <https://django-filter.readthedocs.io/>`_
to filter queryset for export. Set ``filterset_class`` attribute to your resource class and pass
filter parameters as ``filter_kwargs`` argument to resource:


**filters.py**

.. code-block:: python

    from django_filters import rest_framework as filters

    from . import models


    class BandFilterSet(filters.FilterSet):

        class Meta:
            model = models.Band
            fields = [
                "id",
                "title",
            ]


**resources.py**

.. code-block:: python

    from import_export_extensions import resources
    from . import filters
    from . import models


    class BandResource(resources.CeleryModelResource):

        filterset_class = filters.BandFilterSet

        class Meta:
            model = models.Band
            fields = ["id", "title"]

If ``filterset_class`` is set for your resource, you can pass ``filter_kwargs`` to filter export
queryset:

.. code-block:: python
    :linenos:

    >>> from .resources import BandResource
    >>> from .models import Band
    >>> Band.objects.bulk_create([Band(title=title) for title in "ABC"])
    >>> BandResource().get_queryset().count()
    3
    >>> filter_kwargs = {"title": "A"}
    >>> band_resource_with_filters = BandResource(filter_kwargs=filter_kwargs)
    >>> band_resource_with_filters.get_queryset().count()
    1

Pass ``filter_kwargs`` in ``resource_kwargs`` argument to create ``ExportJob`` with filtered queryset:

.. code-block:: python
    :linenos:

    >>> export_job = ExportJob.objects.create(
            resource_path=BandResource.class_path,
            file_format_path=file_format_path,
            resource_kwargs={"filter_kwargs": filter_kwargs},
        )
    >>> export_job.refresh_from_db()
    >>> len(export_job.result)
    1

Since we are using the rest framework filter set, ``ExportJobViewSet`` also supports it. It takes
the filter set from ``resource_class``. You can see that ``start`` action expects query parameters
for filtering:

.. figure:: _static/images/filters-openapi.png


-------
Widgets
-------

This package also provides additional widgets for some types of data.

FileWidget
__________

Working with file fields is a common issue. ``FileWidget`` allows to import/export files
including links to external resources that store files and save them in ``DEFAULT_FILE_STORAGE``.

This widget loads a file from link to media dir. And it correctly render the link for export. It
also supports ``AWS_STORAGE_BUCKET_NAME`` setting.


IntermediateManyToManyWidget
____________________________

``IntermediateManyToManyWidget`` allows to import/export objects with related items.
Default M2M widget store just IDs of related objects. With intermediate widget
additional data may be stored. Should be used with ``IntermediateManyToManyField``.

------
Fields
------

M2MField
________

This is resource field for M2M fields. Provides faster import of related fields.

    This implementation deletes intermediate models, which were excluded
    and creates intermediate models only for newly added models.

IntermediateManyToManyField
___________________________

This is resource field for M2M with custom ``through`` model.

    By default, ``django-import-export`` set up object attributes using
    ``setattr(obj, attribute_name, value)``, where ``value`` is ``QuerySet``
    of related model objects. But django forbid this when ``ManyToManyField``
    used with custom ``through`` model.

    This field expects be used with custom ``IntermediateManyToManyWidget`` widget
    that return not simple value, but dict with intermediate model attributes.
