=======
History
=======
UNRELEASED
------------------
* Fix progress bar on changeview for ImportJob and ExportJob
* Improve celery-import-result page

  * Add displaying resources for import form
  * Fix autofill `Format` by file extension
  * Add `Totals` section
  * Remove extra loop if errors in input file (https://github.com/saritasa-nest/django-import-export-extensions/issues/74)

* Fixed display of progress bar when task is waiting to run (https://github.com/saritasa-nest/django-import-export-extensions/issues/68)
* Improve progress bar style (https://github.com/saritasa-nest/django-import-export-extensions/issues/72)
* Set `default_auto_field` for `import-export-extensions` app to `django.db.models.BigAutoField` (https://github.com/saritasa-nest/django-import-export-extensions/issues/69)

1.0.1 (2024-11-08)
------------------
* Replaced `sphinx-rtd-theme` by [furo](https://github.com/pradyunsg/furo)
* Update/extend documentation
* Support Python 3.13
* Drop Django <4.2 support

0.7.0 (2024-10-29)
------------------
* Add support django-import-export >= 4.2
* Removed support for django-import-export < 4.2
* Improve test coverage

0.6.1 (2024-10-04)
------------------
* Update requirements version and internal naming

0.6.0 (2024-10-04)
------------------
* Extend response of import job api
* Added support for django-import-export >= 4.0
* Removed support for django 3.2
* Add search and ordering to API views
* Removed `M2MField` since `import_export.fields.Field` supports `m2m_add`

0.5.0 (2023-12-19)
------------------
* Drop support of python 3.9
* Migrate from pip-tools to poetry
* Add base model for ``ImportJob`` and ``ExportJob``
* Extend import results template: show validation errors in table
* Add force-import feature: skip rows with errors while importing
* Add ``skip_parse_step`` parameter for importing API
* Remove Makefile in favor of ``invoke`` commands

0.4.1 (2023-09-25)
------------------
* Remove ``escape_output`` due it's deprecation

0.4.0 (2023-09-11)
------------------
* Make possible to pass ``resource_kwargs`` in ViewSets
* Remove filter_set from ImportViewSet

0.3.1 (2023-09-11)
------------------
* Add more detailed documentation for package features

0.3.0 (2023-09-11)
------------------
* Support settings from original package

0.2.0 (2023-08-25)
------------------
* Improve GitHub workflow name
* Get rid of DjangoObjectActions and implement default django admin action instead (Maybe later we can extend this)
* Use mixins.BaseExportMixin, mixins.BaseImportMixin and admin.ImportExportMixinBase from original package for celery admin mixins
* Use admin/import_export/ templates instead of copies in admin/import_export_extensions/
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
