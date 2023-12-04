##############################################################################
# Commands used in ci for code validation
##############################################################################
import saritasa_invocations
from invoke import task


@task
def prepare(context):
    """Prepare ci environment for check."""
    saritasa_invocations.print_success("Preparing CI")
    saritasa_invocations.docker.up(context)
    saritasa_invocations.github_actions.set_up_hosts(context)
    saritasa_invocations.poetry.install(context)


@task
def coverage(context):
    """Run tests through coverage to generate coverage report."""
    saritasa_invocations.python.run(
        context,
        command="-m coverage run -m pytest -v",
    )
