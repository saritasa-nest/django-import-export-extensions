##############################################################################
# Run commands
##############################################################################

def run_python(context, command: str, watchers=()):
    """Run command using local python interpreter."""
    return context.run(
        " ".join(["python3", command]),
        watchers=watchers,
    )
