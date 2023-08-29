====================
API (Rest Framework)
====================

.. autoclass:: import_export_extensions.api.views.ImportJobViewSet
   :members:

.. autoclass:: import_export_extensions.api.views.ExportJobViewSet
   :members:

.. autoclass:: import_export_extensions.api.CreateExportJob
   :members: create, validate

.. autoclass:: import_export_extensions.api.CreateImportJob
   :members: create, validate

.. autoclass:: import_export_extensions.api.ExportJobSerializer
   :members:

.. autoclass:: import_export_extensions.api.ImportJobSerializer
   :members:

.. autoclass:: import_export_extensions.api.ProgressSerializer
   :members:

    .. attribute:: info
       :type: ProgressInfoSerializer
       :value: {"current": 0, "total": 0}

        Shows current and total imported/exported values

.. autoclass:: import_export_extensions.api.ProgressInfoSerializer
   :members:

    .. attribute:: current
       :type: int
       :value: 0

       Shows number of imported/exported objects

    .. attribute:: total
       :type: int
       :value: 0

       Shows total objects to import/export
