.. highlight:: shell

============
Contributing
============

Contributions are welcome, and they are greatly appreciated! Every little bit
helps, and credit will always be given.

You can contribute in many ways:

Types of Contributions
----------------------

Report Bugs
~~~~~~~~~~~

Report bugs at https://github.com/saritasa-nest/django-import-export-extensions/issues.

If you are reporting a bug, please include:

* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix Bugs
~~~~~~~~

Look through the GitHub issues for bugs. Anything tagged with "bug" and "help
wanted" is open to whoever wants to implement it.

Implement Features
~~~~~~~~~~~~~~~~~~

Look through the GitHub issues for features. Anything tagged with "enhancement"
and "help wanted" is open to whoever wants to implement it.

Write Documentation
~~~~~~~~~~~~~~~~~~~

``django-import-export-extensions`` could always use more documentation, whether as part of the
official ``django-import-export-extensions`` docs, in docstrings, or even on the web in blog posts,
articles, and such.

Submit Feedback
~~~~~~~~~~~~~~~

The best way to send feedback is to file an issue at https://github.com/saritasa-nest/django-import-export-extensions/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

Get Started!
------------

Ready to contribute? Here's how to set up `django-import-export-extensions` for local development.

1. Fork the `django-import-export-extensions` repo on GitHub.
2. Clone your fork locally::

    git clone git@github.com:your_name_here/django-import-export-extensions.git

3. Setup virtual environment:

  Using pyenv::

    pyenv install 3.13
    pyenv shell $(pyenv latest 3.13)
    poetry config virtualenvs.in-project true
    source .venv/bin/activate && poetry install

  Using uv::

    uv venv --python 3.13 --prompt django-import-export-extensions --seed
    poetry config virtualenvs.in-project true
    source .venv/bin/activate && poetry install

4. Create a branch for local development::

    git checkout -b name-of-your-bugfix-or-feature

   Now you can make your changes locally.

5. When you're done making changes, check that your changes pass linters and the
   tests::

    inv pre-commit.run-hooks

6. Commit your changes and push your branch to GitHub::

    git add .
    git commit -m "Your detailed description of your changes."
    git push origin name-of-your-bugfix-or-feature

7. Submit a pull request through the GitHub website.

Pull Request Guidelines
-----------------------

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring, and add the
   feature to the list in README.md.
3. The pull request should work for each supported Python version, and for PyPy. Check
   github actions status, verify that all checks have been passed.
