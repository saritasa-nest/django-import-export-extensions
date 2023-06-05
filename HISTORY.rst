=======
History
=======

0.1.5 (2023-06-07)
------------------
* Add support for multiple resource classes in model admin
* Refactor CeleryExportAdminMixin, CeleryImportAdminMixin
    * move common logic to a base class
    * drop `get_export_formats`, `get_import_formats` methods: call the corresponding methods on resource class instead

0.1.4 (2023-05-22)
------------------
* Add coverage badge

0.1.3 (2023-05-15)
------------------
* Migrate from ``setup.py`` and ``setup.cfg`` to ``pyproject.toml``

0.1.2 (2023-05-12)
------------------

* Add support for `STORAGES` settings variable

0.1.1 (2023-04-27)
------------------

* Add package description
* Add configuration file for read-the-docs service

0.1.0 (2023-04-01)
------------------

* First release on PyPI.
