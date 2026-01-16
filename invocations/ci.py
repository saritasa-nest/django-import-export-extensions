import invoke
import saritasa_invocations


@invoke.task
def prepare(context: invoke.Context) -> None:
    """Prepare ci environment for check."""
    saritasa_invocations.print_success("Preparing CI")
    saritasa_invocations.docker.up(context)
    saritasa_invocations.github_actions.set_up_hosts(context)
    saritasa_invocations.poetry.install(context)
