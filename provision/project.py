from invoke import task

from . import common, django, docker, git, linters, tests


##############################################################################
# Build project locally
##############################################################################
@task
def init(context, clean=False):
    """Prepare env for working with project."""
    common.success("Setting up git config")
    git.setup(context)
    common.success("Initial assembly of all dependencies")
    install_tools(context)
    install_requirements(context)
    if clean:
        docker.clear(context)
    django.migrate(context)
    tests.run(context)
    linters.all(context)
    django.createsuperuser(context)


##############################################################################
# Manage dependencies
##############################################################################
@task
def install_tools(context):
    """Install shell/cli dependencies, and tools needed to install requirements

    Define your dependencies here, for example:
    local("sudo npm -g install ngrok")

    """
    context.run("pip install --upgrade setuptools pip pip-tools wheel")


@task
def install_requirements(context, env="development"):
    """Install local development requirements"""
    common.success(f"Install requirements with pip from {env}.txt")
    context.run(f"pip install -r requirements/{env}.txt")
