from invoke import Exit, UnexpectedExit, task

from . import common

##############################################################################
# Linters
##############################################################################

DEFAULT_FOLDERS = "import_export_extensions tests"


@task
def isort(context, path=DEFAULT_FOLDERS, params=""):
    """Command to fix imports formatting."""
    common.success("Linters: ISort running")
    return context.run(command=f"isort {path} {params}")


@task
def isort_check(context, path=DEFAULT_FOLDERS):
    """Command to fix imports formatting."""
    return isort(context, path=path, params="--check-only")


@task
def flake8(context, path=DEFAULT_FOLDERS):
    """Run `flake8` linter."""
    common.success("Linters: Flake8 running")
    return context.run(command=f"flake8 {path}")


@task
def mypy(context, path=DEFAULT_FOLDERS):
    """Run `mypy` linter."""
    common.success("Linters: Mypy running")
    return context.run(
        command=f"mypy --install-types --non-interactive {path}",
    )


@task
def all(context, path=DEFAULT_FOLDERS):
    """Run all linters"""
    common.success("Linters: running all linters")
    linters = (isort_check, flake8, mypy)
    failed = []
    for linter in linters:
        try:
            linter(context, path)
        except UnexpectedExit:
            failed.append(linter.__name__)
    if failed:
        common.error(
            f"Linters failed: {', '.join(map(str.capitalize, failed))}",
        )
        raise Exit(code=1)
