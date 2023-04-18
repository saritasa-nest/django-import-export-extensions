from invoke import task


@task
def run(context):
    """Start celery worker."""
    context.run(
        "celery --app config.celery:app "
        "worker --beat --scheduler=django --loglevel=info",
    )
