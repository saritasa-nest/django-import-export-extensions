# Django-import-export-extensions

[![PyPI - Python Versions](https://img.shields.io/pypi/pyversions/django-import-export-extensions)](https://pypi.org/project/django-import-export-extensions/)
[![PyPI - Django Versions](https://img.shields.io/pypi/frameworkversions/django/django-import-export-extensions)](https://pypi.org/project/django-import-export-extensions/)
![PyPI](https://img.shields.io/pypi/v/django-import-export-extensions)

[![Build status on Github](https://github.com/saritasa-nest/django-import-export-extensions/actions/workflows/checks.yml/badge.svg)](https://github.com/saritasa-nest/django-import-export-extensions/actions/workflows/checks.yml)
[![Test coverage](https://coveralls.io/repos/github/saritasa-nest/django-import-export-extensions/badge.svg?branch=main)](https://coveralls.io/github/saritasa-nest/django-import-export-extensions?branch=main)
[![Documentation Status](https://readthedocs.org/projects/django-import-export-extensions/badge/?version=latest)](https://django-import-export-extensions.readthedocs.io/en/latest/?badge=latest)

 ![PyPI Downloads](https://static.pepy.tech/badge/django-import-export-extensions/month)

## Links

- [Documentation](<https://django-import-export-extensions.readthedocs.io>)
- [GitHub](<https://github.com/saritasa-nest/django-import-export-extensions>)
- [PyPI](<https://pypi.org/project/django-import-export-extensions>)
- [Contibuting](<https://django-import-export-extensions.readthedocs.io/en/stable/contributing.html>)
- [History](https://django-import-export-extensions.readthedocs.io/en/stable/history.html)

## Description

`django-import-export-extensions` extends the functionality of
[django-import-export](https://github.com/django-import-export/django-import-export/)
adding the following features:

- Import/export resources in the background via Celery
- Manage import/export jobs via Django Admin
- DRF integration that allows to work with import/export jobs via API
- Support [drf-spectacular](https://github.com/tfranzel/drf-spectacular) generated API schema
- Additional fields and widgets (FileWidget, IntermediateManyToManyWidget, IntermediateManyToManyField)

## Installation

To install `django-import-export-extensions`, run this command in your
terminal:

```sh
pip install django-import-export-extensions
```

Add `import_export` and `import_export_extensions` to `INSTALLED_APPS`

```python
# settings.py
INSTALLED_APPS = (
    ...,
    "import_export",
    "import_export_extensions",
)
```

Run `migrate` command to create ImportJob/ExportJob models and
`collectstatic` to let Django collect package static files to use in the
admin.

```sh
python manage.py migrate
python manage.py collectstatic
```

## Usage

Prepare resource for your model

```python
# apps/books/resources.py
from import_export_extensions.resources import CeleryModelResource

from .. import models


class BookResource(CeleryModelResource):

    class Meta:
        model = models.Book
```

Use `CeleryImportExportMixin` class and set `resource_classes` in admin
model to import/export via Django Admin

```python
# apps/books/admin.py
from django.contrib import admin

from import_export_extensions.admin import CeleryImportExportMixin

from .. import resources


@admin.register(models.Book)
class BookAdmin(CeleryImportExportMixin, admin.ModelAdmin):
    resource_classes = [resources.BookResource]
```

Prepare view sets to import/export via API

``` python
# apps/books/api/views.py
from .. import resources

from import_export_extensions.api import views


class BookExportViewSet(views.ExportJobViewSet):
    resource_class = resources.BookResource


class BookImportViewSet(views.ImportJobViewSet):
    resource_class = resources.BookResource
```

Don't forget to [configure
Celery](https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html)
if you want to run import/export in background

## License

- Free software: MIT license
