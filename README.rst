===============================
django-import-export-extensions
===============================

.. image:: https://github.com/saritasa-nest/django-import-export-extensions/actions/workflows/checks.yml/badge.svg
    :target: https://github.com/saritasa-nest/django-import-export-extensions/actions/workflows/checks.yml
    :alt: Build status on Github

.. image:: https://coveralls.io/repos/github/saritasa-nest/django-import-export-extensions/badge.svg?branch=main
    :target: https://coveralls.io/github/saritasa-nest/django-import-export-extensions?branch=main
    :alt: Test coverage

.. image:: https://img.shields.io/pypi/pyversions/django-import-export-extensions
    :target: https://pypi.org/project/django-import-export-extensions/
    :alt: Supported python versions

.. image:: https://img.shields.io/badge/django--versions-4.0_%7C_4.1_%7C_4.2_%7C_5.0-blue
    :target: https://pypi.org/project/django-import-export-extensions/
    :alt: Supported django versions

.. image:: https://readthedocs.org/projects/django-import-export-extensions/badge/?version=latest
    :target: https://django-import-export-extensions.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://static.pepy.tech/personalized-badge/django-import-export-extensions?period=month&units=international_system&left_color=gray&right_color=blue&left_text=Downloads/month
    :target: https://pepy.tech/project/django-import-export-extensions
    :alt: Downloading statistic

Description
-----------
``django-import-export-extensions`` extends the functionality of
`django-import-export <https://github.com/django-import-export/django-import-export/>`_
adding the following features:

* Import/export resources in the background via Celery
* Manage import/export jobs via Django Admin
* DRF integration that allows to work with import/export jobs via API
* Support `drf-spectacular <https://github.com/tfranzel/drf-spectacular>`_ generated API schema
* Additional fields and widgets (FileWidget, IntermediateManyToManyWidget, IntermediateManyToManyField)

Installation
------------

To install ``django-import-export-extensions``, run this command in your terminal:

.. code-block:: console

    $ pip install django-import-export-extensions

Add ``import_export`` and ``import_export_extensions`` to ``INSTALLED_APPS``

.. code-block:: python

    # settings.py
    INSTALLED_APPS = (
        ...,
        "import_export",
        "import_export_extensions",
    )

Run ``migrate`` command to create ImportJob/ExportJob models and
``collectstatic`` to let Django collect package static files to use in the admin.

.. code-block:: shell

    $ python manage.py migrate
    $ python manage.py collectstatic


Usage
-----

Prepare resource for your model

.. code-block:: python

    # apps/books/resources.py
    from import_export_extensions.resources import CeleryModelResource

    from .. import models


    class BookResource(CeleryModelResource):

        class Meta:
            model = models.Book

Use ``CeleryImportExportMixin`` class and set ``resource_class`` in admin model
to import/export via Django Admin

.. code-block:: python

    # apps/books/admin.py
    from django.contrib import admin

    from import_export_extensions.admin import CeleryImportExportMixin

    from .. import resources


    @admin.register(models.Book)
    class BookAdmin(CeleryImportExportMixin, admin.ModelAdmin):
        resource_class = resources.BookResource


Prepare view sets to import/export via API

.. code-block:: python

    # apps/books/api/views.py
    from .. import resources

    from import_export_extensions.api import views


    class BookExportViewSet(views.ExportJobViewSet):
        resource_class = resources.BookResource


    class BookImportViewSet(views.ImportJobViewSet):
        resource_class = resources.BookResource


Don't forget to `configure Celery <https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html>`_
if you want to run import/export in background


Links:
------
* Documentation: https://django-import-export-extensions.readthedocs.io.
* GitHub: https://github.com/saritasa-nest/django-import-export-extensions/
* PyPI: https://pypi.org/project/django-import-export-extensions/

License:
--------
* Free software: MIT license
