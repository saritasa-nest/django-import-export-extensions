=======
History
=======

Unreleased
------------------

* Support Django 6.0
* Keep the IDs of search and filter results from the admin, instead of using
  a reimplementation of the Django admin code

1.9.2 (2025-11-6)
------------------

* Change dependency versions constraints

1.9.1 (2025-10-28)
------------------

* Support Python 3.14

1.9.0 (2025-09-16)
------------------

* Improve filterset class initialization during fetching export queryset
* Add ability to customize the order of operation for export queryset
* Add ability to set dataset title
* Add field selection to the export confirmation page in the admin panel
* Add support to skip export confirmation page in admin (https://github.com/saritasa-nest/django-import-export-extensions/issues/122):

  * with `IMPORT_EXPORT_SKIP_ADMIN_EXPORT_UI=True` setting from original package
  * with `skip_export_form` flag at the admin model level

1.8.0 (2025-06-30)
------------------

* Add ability to disable celery task updates for resource
* Make that resources will always filter queryset on export if filterset_class is present

1.7.0 (2025-05-22)
------------------

* Add support using admin page filters for export
* Minor refactor of CeleryResourceMixin for easier overriding of export/import methods
* Add ability to pass additional args to `BaseFormat.export_data` on export

1.6.0 (2025-04-29)
------------------

* Support Django 5.2
* Add support for customizing Django Admin forms for import/export

1.5.0 (2025-04-02)
------------------

* Fix issue with long `error_message`
* Add signals `export_job_failed` and `import_job_failed`
  to respond to failed jobs.
* Add ability to specify storage via `STORAGES` setting and alias
  `django_import_export_extensions`
* Make possible to pass args/kwargs to import/export start action

1.4.1 (2025-02-18)
------------------

* Make querysets more consistent for ViewSets

1.4.0 (2025-01-28)
------------------

* Add explicit `created_by` argument to `CeleryResourceMixin` and pass it in
  `ExportJobSerializer` validation
* Add export/import action mixins `api.mixins.ExportStartActionMixin`
  and `api.mixins.ImportStartActionMixin`
* Add `api.views.BaseExportJobViewSet`, `BaseExportJobForUsersViewSet`,
  `api.views.BaseImportJobViewSet` and `BaseImportJobForUsersViewSet` for
  job management

1.3.1 (2025-01-13)
------------------

* Fix issues with query params parsing
* Make `get_queryset` consistent for start actions

1.3.0 (2025-01-09)
------------------

* Add base import/export views that only allow users to work with their own jobs (`ImportJobForUserViewSet` and `ExportJobForUserViewSet`).
* Small actions definition refactor in `ExportJobViewSet/ExportJobViewSet` to allow easier overriding.
* Add support for ordering in `export`
* Add settings for DjangoFilterBackend and OrderingFilter in export api.
  `DRF_EXPORT_DJANGO_FILTERS_BACKEND` with default `django_filters.rest_framework.DjangoFilterBackend` and
  `DRF_EXPORT_ORDERING_BACKEND` with default `rest_framework.filters.OrderingFilter`.

1.2.0 (2024-12-26)
------------------
* Fix issue with slow export duration (https://github.com/saritasa-nest/django-import-export-extensions/issues/79):

  * Add setting ``STATUS_UPDATE_ROW_COUNT`` (default: 100) which defines the number of rows after import/export of which the task status is updated;
  * Add ability to specify ``status_update_row_count`` for each resource;

1.1.0 (2024-12-06)
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
