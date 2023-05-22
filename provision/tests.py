from invoke import task

from . import common, start


@task
def run(context, params=""):
    """Run django tests with ``extra`` args for ``p`` tests.

    `p` means `params` - extra args for tests
    python -m pytest <extra>

    """
    common.success("Tests running")
    return start.run_python(context, f"-m pytest {params}")


@task
def run_ci(context):
    """Run tests in github actions."""
    start.run_coverage(
        context,
        "--source import_export_extensions "
        "--omit import_export_extensions/migrations "
        "-m pytest -v",
    )
