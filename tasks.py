from invoke import Collection

from provision import celery, ci, django, docker, git, linters, project, tests

ns = Collection(
    celery,
    ci,
    django,
    docker,
    linters,
    project,
    tests,
    git,
)

# Configurations for run command
ns.configure(
    dict(
        run=dict(
            pty=True,
            echo=True,
        ),
    ),
)
