from invoke import UnexpectedExit, task

from . import common

##############################################################################
# Containers start stop commands
##############################################################################

MAIN_CONTAINERS = (
    "postgres",
    "redis",
)


def stop_all_containers(context):
    """Shortcut for stopping ALL running docker containers."""
    context.run("docker stop $(docker ps -q)")


def up_containers(
    context,
    containers: tuple[str, ...],
    detach=True,
    stop_others=True,
    **kwargs,
):
    """Bring up containers and run them.

    Add `d` kwarg to run them in background.

    Args:
        context: Invoke context
        containers: Name of containers to start
        detach: To run them in background
        stop_others: Stop ALL other containers in case of errors during `up`.
            Usually this happens when containers from other project uses the
            same ports, for example, Postgres and redis.

    Raises:
        UnexpectedExit: when `up` command wasn't successful

    """
    if containers:
        common.success(f"Bring up {', '.join(containers)} containers")
    else:
        common.success("Bring up all containers")
    up_cmd = (
        f"docker compose up "
        f"{'-d ' if detach else ''}"
        f"{' '.join(containers)}"
    )
    try:
        context.run(up_cmd)
    except UnexpectedExit as exception:
        if not stop_others:
            raise exception
        stop_all_containers(context)
        context.run(up_cmd)


def stop_containers(context, containers):
    """Stop containers."""
    common.success(f"Stopping {' '.join(containers)} containers ")
    cmd = f"docker compose stop {' '.join(containers)}"
    context.run(cmd)


@task
def up(context):
    """Bring up main containers and start them."""
    up_containers(
        context,
        containers=MAIN_CONTAINERS,
        detach=True,
    )


@task
def stop(context):
    """Stop main containers."""
    stop_containers(
        context,
        containers=MAIN_CONTAINERS,
    )


@task
def clear(context):
    """Stop and remove all containers defined in docker-compose.

    Also remove images.

    """
    common.success("Clearing docker compose")
    context.run("docker compose rm -f")
    context.run("docker compose down -v --rmi all --remove-orphans")
