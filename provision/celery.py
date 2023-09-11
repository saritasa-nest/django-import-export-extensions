from invoke import task


@task
def run(context):
    """Start celery worker."""
    context.run(
        "celery --app tests.celery_app:app "
        "worker --beat --scheduler=django --loglevel=info",
    )
