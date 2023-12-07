import pathlib

import invoke
import saritasa_invocations

LOCAL_DOCS_DIR = pathlib.Path("docs/_build")


@invoke.task
def build(context: invoke.Context):
    """Build documentation."""
    saritasa_invocations.print_success("Start building of local documentation")
    context.run(f"sphinx-build -E -a docs {LOCAL_DOCS_DIR}")
    saritasa_invocations.print_success("Building completed")
