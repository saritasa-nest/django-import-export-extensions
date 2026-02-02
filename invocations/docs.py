import invoke
import saritasa_invocations


@invoke.task
def build(context: invoke.Context) -> None:
    """Build documentation."""
    saritasa_invocations.print_success("Start building of local documentation")
    context.run("mkdocs build")
    saritasa_invocations.print_success("Building completed")


@invoke.task
def serve(context: invoke.Context) -> None:
    """Serve documentation locally."""
    saritasa_invocations.print_success("Start serving local documentation")
    context.run("mkdocs serve")
    saritasa_invocations.print_success("Serving completed")
