.. highlight:: shell

==============================
Installation and Configuration
==============================


Stable release
--------------

To install django-import-export-extensions, run this command in your terminal:

.. code-block:: console

    $ pip install django-import-export-extensions

This is the preferred method to install django-import-export-extensions, as it will always install the most recent stable release.

If you don't have `pip`_ installed, this `Python installation guide`_ can guide
you through the process.

.. _pip: https://pip.pypa.io
.. _Python installation guide: http://docs.python-guide.org/en/latest/starting/installation/


From sources
------------

The sources for django-import-export-extensions can be downloaded from the `Github repo`_.

You can either clone the public repository:

.. code-block:: console

    $ git clone https://github.com/saritasa-nest/django-import-export-extensions

Or download the `tarball`_:

.. code-block:: console

    $ curl -OJL https://github.com/saritasa-nest/django-import-export-extensions/tarball/master

Once you have a copy of the source, you can install it with:

.. code-block:: console

    $ python setup.py install


.. _Github repo: https://github.com/saritasa-nest/django-import-export-extensions
.. _tarball: https://github.com/saritasa-nest/django-import-export-extensions/tarball/master


Add `import_export_extensions` to INSTALLED_APPS

.. code-block:: python

    # settings.py
    INSTALLED_APPS = (
        ...
        'import_export_extensions',
    )

And then run `migrate` command to create ImportJob/ExportJob models and
`collectstatic` to let Django collect package static files to use in the admin.

.. code-block:: shell

    $ python manage.py migrate
    $ python manage.py collectstatic


Celery
------

You need to `set up Celery <https://docs.celeryq.dev/en/latest/getting-started/first-steps-with-celery.html>`_
to use background import/export. Just plug in Celery and you don't need additional
settings.


Settings
-------------

You can configure the following in your settings file:

``IMPORT_EXPORT_MAX_DATASET_ROWS``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sets the maximum number of lines in the file to import in order to avoid memory
overflow. The default value is 10,000. If there are more lines in the file,
a ``ValueError`` exception will be raised on import.

``MIME_TYPES_MAP``
~~~~~~~~~~~~~~~~~~

Mapping file extensions to mime types to import files.
Default is `mimetypes.types_map`.


Settings from django-import-export
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There are also available `settings from original django-import-export
<https://django-import-export.readthedocs.io/en/latest/installation.html#settings>`_
package.
