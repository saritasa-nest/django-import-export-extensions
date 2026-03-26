# How to contribute

Contributions are welcome, and they are greatly appreciated! Every
little bit helps, and credit will always be given.

You can contribute in many ways:

## Types of Contributions

### Report Bugs

Report bugs at
<https://github.com/saritasa-nest/django-import-export-extensions/issues>.

If you are reporting a bug, please include:

- Any details about your local setup that might be helpful in
    troubleshooting.
- Detailed steps to reproduce the bug.

### Fix Bugs

Look through the GitHub issues for bugs. Anything tagged with `bug`
and `help wanted` is open to whoever wants to implement it.

### Implement Features

Look through the GitHub issues for features. Anything tagged with
`enhancement` and `help wanted` is open to whoever wants to
implement it.

### Write Documentation

`django-import-export-extensions` could always use more documentation,
whether as part of the official `django-import-export-extensions` docs,
in docstrings, or even on the web in blog posts, articles, and such.

The best way to send feedback is to file an issue at
<https://github.com/saritasa-nest/django-import-export-extensions/issues>.

If you are proposing a feature:

- Explain in detail how it would work.
- Keep the scope as narrow as possible, to make it easier to
  implement.
- Remember that this is a volunteer-driven project, and that
  contributions are welcome :)

## Get Started

Ready to contribute? Here's how to set up `django-import-export-extensions`
for local development.

Fork the [django-import-export-extensions](https://github.com/saritasa-nest/django-import-export-extensions) repo on GitHub.
And then clone your fork locally:

```bash
git clone git@github.com:your_name_here/django-import-export-extensions.git
```

Then, navigate to the project directory:

```bash
cd django-import-export-extensions
```

### Setup virtual environment

We use [uv](https://docs.astral.sh/uv/) to manage the dependencies.

To set up venv you would need to run `sync` command:

```bash
uv sync --all-packages --all-groups --all-extras
```

To activate your `virtualenv`

```bash
source .venv/bin/activate
```

### Check code

We use `pre-commit` for quality control.

To run checks:

```bash
inv pre-commit.run-hooks
```

## Pull Request Guidelines

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated.
   Put your new functionality into a function with a docstring, and add
   the feature to the list in README.md.
3. The pull request should work for each supported Python version.
   Check github actions status, verify that all checks have been passed.
