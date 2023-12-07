import pathlib
import shutil

import invoke
import saritasa_invocations


@invoke.task
def init(context: invoke.Context, clean: bool = False):
    """Prepare env for working with project."""
    saritasa_invocations.print_success("Setting up git config")
    saritasa_invocations.git.setup(context)
    saritasa_invocations.print_success("Initial assembly of all dependencies")
    saritasa_invocations.poetry.install(context)
    if clean:
        saritasa_invocations.docker.clear(context)
        clear(context)
    saritasa_invocations.django.migrate(context)
    saritasa_invocations.pytest.run(context)
    saritasa_invocations.django.createsuperuser(context)


@invoke.task
def clear(context: invoke.Context):
    """Clear package directory from cache files."""
    saritasa_invocations.print_success("Start clearing")
    build_dirs = ("build", "dist", ".eggs")
    coverage_dirs = ("htmlcov",)
    cache_dirs = (".mypy_cache", ".pytest_cache")

    saritasa_invocations.print_success("Remove cache directories")
    for directory in build_dirs + coverage_dirs + cache_dirs:
        shutil.rmtree(directory, ignore_errors=True)

    cwd = pathlib.Path(".")
    # remove egg paths
    saritasa_invocations.print_success("Remove egg directories")
    for path in cwd.glob("*.egg-info"):
        shutil.rmtree(path, ignore_errors=True)

    for path in cwd.glob("*.egg"):
        path.unlink(missing_ok=True)

    # remove last coverage file
    saritasa_invocations.print_success("Remove coverage file")
    pathlib.Path(".coverage").unlink(missing_ok=True)
