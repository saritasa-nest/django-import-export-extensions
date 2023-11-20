##############################################################################
# Commands used in ci for code validation
##############################################################################
from invoke import task

from . import common, docker, project


@task
def prepare(context):
    """Prepare ci environment for check."""
    common.success("Preparing CI")
    docker.up(context)
    set_up_hosts(context)
    project.install_requirements(context)


def set_up_hosts(context):
    """Add services to hosts."""
    common.success("Setting up hosts")
    context.run("echo \"127.0.0.1 postgres\" | sudo tee -a /etc/hosts")
    context.run("echo \"127.0.0.1 redis\" | sudo tee -a /etc/hosts")
