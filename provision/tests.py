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
    run(context, params="-v")
