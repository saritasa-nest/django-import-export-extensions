===============================
Django import/export extensions
===============================

django-import-export-extensions is a Django application and library based on
`django-import-export` library that provided extended features.

**Features:**

* Import/export :ref:`resources<Resources>` in the background via Celery
* Manage import/export :ref:`jobs<ImportJob/ExportJob models>` via Django Admin
* :ref:`DRF integration<ViewSets>` that allows to work with import/export jobs via API
* Support `drf-spectacular <https://github.com/tfranzel/drf-spectacular>`_ generated API schema
* Additional :ref:`fields<Fields>` and :ref:`widgets<Widgets>` (FileWidget, IntermediateM2MWidget, M2MField)

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   installation
   getting_started
   extensions
   migrate_from_original_import_export
   authors
   history

.. toctree::
   :maxdepth: 2
   :caption: API Documentation

   api_admin
   api_models
   api_drf

.. toctree::
   :maxdepth: 2
   :caption: Developers

   contributing


Indices and tables
==================
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
