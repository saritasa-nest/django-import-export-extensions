import invoke
import saritasa_invocations

import invocations

ns = invoke.Collection(
    invocations.ci,
    invocations.docs,
    invocations.project,
    saritasa_invocations.pytest,
    saritasa_invocations.uv,
    saritasa_invocations.git,
    saritasa_invocations.pre_commit,
    saritasa_invocations.mypy,
    saritasa_invocations.python,
    saritasa_invocations.celery,
    saritasa_invocations.django,
    saritasa_invocations.docker,
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
                app="test_project.celery_app:app",
                scheduler="",
                extra_params=("",),
            ),
            django=saritasa_invocations.DjangoSettings(
                manage_file_path="test_project/manage.py",
                settings_path="test_project.settings",
                apps_path="test_project",
            ),
            github_actions=saritasa_invocations.GitHubActionsSettings(
                hosts=("postgres", "redis"),
            ),
        ),
    },
)
