import os

import invoke
import saritasa_invocations


@invoke.task
def prepare(context: invoke.Context) -> None:
    """Prepare ci environment for check."""
    saritasa_invocations.print_success("Preparing CI")
<<<<<<< before updating
    saritasa_invocations.uv.sync(context)
    saritasa_invocations.docker.up(context)
    saritasa_invocations.github_actions.set_up_hosts(context)
    context.run(f'uv pip install "django{os.environ["DJANGO_VERSION"]}"')
=======
>>>>>>> after updating


@invoke.task
def run_pre_commit(context: invoke.Context) -> None:
    """Run pre-commit hooks."""
    saritasa_invocations.pre_commit.run_hooks(context)
