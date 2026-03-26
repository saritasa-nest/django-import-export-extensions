import invoke
import saritasa_invocations


@invoke.task
def init(context: invoke.Context, clean: bool = False) -> None:
    """Prepare env for working with project."""
    saritasa_invocations.print_success("Setting up git config")
    saritasa_invocations.git.setup(context)
    saritasa_invocations.system.copy_vscode_settings(context)
    saritasa_invocations.print_success("Initial assembly of all dependencies")
    saritasa_invocations.uv.sync(context)
    if clean:
        saritasa_invocations.docker.clear(context)
    saritasa_invocations.django.migrate(context)
    saritasa_invocations.pytest.run(context)
    saritasa_invocations.django.createsuperuser(context)
