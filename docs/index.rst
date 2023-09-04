===============================
Django import/export extensions
===============================

django-import-export-extensions is a Django application and library based on
`django-import-export` library that provided extended features.

**Features:**

* Import/export resources in the background via Celery
* Manage import/export jobs via Django Admin
* DRF integration that allows to work with import/export jobs via API
* Support `drf-spectacular <https://github.com/tfranzel/drf-spectacular>`_ generated API schema
* Additional fields and widgets (FileWidget, IntermediateM2MWidget, M2MField)

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   installation
   migrate_from_original_import_export
   getting_started
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
