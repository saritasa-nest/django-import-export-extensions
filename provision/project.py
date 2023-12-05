import saritasa_invocations
from invoke import task


@task
def init(context, clean=False):
    """Prepare env for working with project."""
    saritasa_invocations.print_success("Setting up git config")
    saritasa_invocations.git.setup(context)
    saritasa_invocations.print_success("Initial assembly of all dependencies")
    saritasa_invocations.poetry.install(context)
    if clean:
        saritasa_invocations.docker.clear(context)
    saritasa_invocations.django.migrate(context)
    saritasa_invocations.pytest.run(context)
    saritasa_invocations.django.createsuperuser(context)
