=======
History
=======

0.1.5 (2023-05-22)
------------------
* Improve GitHub workflow name
* Get rid of DjangoObjectActions and implement default django admin action instead (Maybe later we can extend this)
* Use mixins.BaseExportMixin, mixins.BaseImportMixin and admin.ImportExportMixinBase from original package for celery admin mixins
* Use admin/import_export/ templates instead of copies in admin/import_export_ext/
* Small improvements:

    * Fix static folder name
    * Fix invoke command to run celery
    * Fix progress bar widget
    * Rename filter_class to filterset_class
    * Add cancel_job action for exporting

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
