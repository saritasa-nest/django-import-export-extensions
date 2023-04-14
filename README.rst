===============================
django-import-export-extensions
===============================

.. image:: https://github.com/saritasa-nest/django-import-export-extensions/actions/workflows/checks.yml/badge.svg
        :target: https://github.com/saritasa-nest/django-import-export-extensions/actions/workflows/checks.yml
        :alt: Build status on Github

.. image:: https://img.shields.io/badge/python%20versions-3.9%20%7C%203.10%20%7C%203.11-blue
        :target: https://img.shields.io/badge/python%20versions-3.9%20%7C%203.10%20%7C%203.11-blue
        :alt: Supported python versions

.. image:: https://img.shields.io/badge/django--versions-3.2%20%7C%204.0%20%7C%204.1%20%7C%204.2-blue
        :target: https://img.shields.io/badge/django--versions-3.2%20%7C%204.0%20%7C%204.1%20%7C%204.2-blue
        :alt: Supported django versions


Description
-----------
`django-import-export-extensions` extends the functionality of
`django-import-export <https://github.com/django-import-export/django-import-export/>`_
adding the following features:

* Import/export resources in the background via Celery
* Manage import/export jobs via Django Admin
* DRF integration that allows to work with import/export jobs via API
* Support `drf-spectacular <https://github.com/tfranzel/drf-spectacular>`_ generated API schema
* Additional fields and widgets (FileWidget, IntermediateM2MWidget, M2MField)

Migration from django-import-export
-----------------------------------
Resources migration
^^^^^^^^^^^^^^^^^^^
Change ``Resource`` or ``ModelResource`` to
``CeleryResource`` or ``CeleryModelResource`` respectively.

Admin migration
^^^^^^^^^^^^^^^
Change ``ImportMixin``, ``ExportMixin``, ``ImportExportMixin``
to ``CeleryImportMixin``, ``CeleryExportMixin`` or ``CeleryImportExportMixin`` respectively.

License
-------
* Free software: MIT license
* Documentation: https://django-import-export-extensions.readthedocs.io.
