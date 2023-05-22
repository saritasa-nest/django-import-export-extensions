##############################################################################
# Run commands
##############################################################################

def run_python(context, command: str, watchers=()):
    """Run command using local python interpreter."""
    return context.run(
        " ".join(["python3", command]),
        watchers=watchers,
    )

def run_coverage(context, command: str, watchers=()):
    """Run command using coverage."""
    return context.run(
        " ".join(["coverage run", command]),
        watchers=watchers,
    )
