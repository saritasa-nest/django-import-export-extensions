==========================
Recipes & Integration Tips
==========================

django-tenants integration
--------------------------

You might need additional changes for integration
with `django-tenants <https://github.com/django-tenants/django-tenants>`_.


Change connection schema if it was provided in admin.

.. code-block:: python

    from django.db import connection

    class MyModelResource(CeleryModelResource):
        def __init__(self, *args, **kwargs):

            # If schema_name is provided, switch db schema
            if "schema_name" in kwargs:
                connection.set_schema(kwargs["schema_name"])

            super().__init__(*args, **kwargs)

Pass schema for resource.

.. code-block:: python

    @admin.register(MyModel)
    class MyModelAdmin(CeleryImportExportMixin, admin.ModelAdmin):
        resource_classes = [MyModelResource]

        def get_resource_kwargs(self, request, *args, **kwargs):

            # Pass schema to job
            kwargs["schema_name"] = request.tenant.schema_name

            return super().get_resource_kwargs(request, *args, **kwargs)
