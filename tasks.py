import saritasa_invocations
from invoke import Collection

import provision

ns = Collection(
    provision.project,
    provision.docs,
    provision.ci,
    saritasa_invocations.celery,
    saritasa_invocations.django,
    saritasa_invocations.docker,
    saritasa_invocations.pytest,
    saritasa_invocations.poetry,
    saritasa_invocations.git,
    saritasa_invocations.pre_commit,
    saritasa_invocations.mypy,
    saritasa_invocations.python,
)

# Configurations for run command
ns.configure(
    {
        "run": {
            "pty": True,
            "echo": True,
        },
        "saritasa_invocations": saritasa_invocations.Config(
            project_name="django-import-export-extensions",
            celery=saritasa_invocations.CelerySettings(
                app="tests.celery_app:app",
            ),
            django=saritasa_invocations.DjangoSettings(
                manage_file_path="tests/manage.py",
                settings_path="tests.settings",
                apps_path="tests",
            ),
            github_actions=saritasa_invocations.GitHubActionsSettings(
                hosts=("postgres", "redis"),
            ),
        ),
    },
)
