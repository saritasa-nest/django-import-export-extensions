.. highlight:: shell

==============================
Installation and configuration
==============================


Stable release
--------------

To install ``django-import-export-extensions``, run the following command in your terminal:

Using pip:

.. code-block:: shell

    pip install django-import-export-extensions

Using uv:

.. code-block:: shell

    uv pip install django-import-export-extensions

Using poetry:

.. code-block:: shell

    poetry add django-import-export-extensions

This is the preferred installation method,
as it will always install the most recent stable release of ``django-import-export-extensions``.

Next, add ``import_export`` and ``import_export_extensions`` to your ``INSTALLED_APPS`` setting:

.. code-block:: python

    # settings.py
    INSTALLED_APPS = [
        ...
        "import_export",
        "import_export_extensions",
    ]

Finally, run the ``migrate`` and ``collectstatic`` commands:

* ``migrate``: Creates the ImportJob and ExportJob models.
* ``collectstatic``: Allows Django to collect static files for use in the admin interface.

.. code-block:: shell

    python manage.py migrate
    python manage.py collectstatic


Celery
------

To use background import/export, you need to
`set up Celery <https://docs.celeryq.dev/en/latest/getting-started/first-steps-with-celery.html>`_.
Once Celery is set up, no additional configuration is required.


Settings
-------------

You can configure the following settings in your Django settings file:

``IMPORT_EXPORT_MAX_DATASET_ROWS``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Defines the maximum number of rows allowed in a file for import, helping to avoid memory overflow.
The default value is 10,000. If the file exceeds this limit, a ``ValueError`` exception
will be raised during the import process.

``MIME_TYPES_MAP``
~~~~~~~~~~~~~~~~~~

Mapping file extensions to mime types to import files.
By default, it uses the `mimetypes.types_map <https://docs.python.org/3/library/mimetypes.html#mimetypes.types_map>`_
from Python's mimetypes module.

``STATUS_UPDATE_ROW_COUNT``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Defines the number of rows after import/export of which the task status is
updated. This helps to increase the speed of import/export. The default value
is 100. This parameter can be specified separately for each resource by adding
``status_update_row_count`` to its ``Meta``.

Settings from django-import-export
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Additionally, the package supports settings from the original django-import-export package.
For full details on these settings, refer to the `official documentation <https://django-import-export.readthedocs.io/en/latest/installation.html#settings>`_.

**Note**: The only setting that does not affect functionality in this package is ``IMPORT_EXPORT_TMP_STORAGE_CLASS``,
as the storage is not used in the implementation of ``CeleryImportAdminMixin``.
