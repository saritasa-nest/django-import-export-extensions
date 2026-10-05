import os

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
    saritasa_invocations.open_api,
)

# Configurations for run command
ns.configure(
    {
        "run": {
            "pty": os.environ.get("INVOKE_PTY", "true").lower() == "true",
            "echo": True,
        },
        "saritasa_invocations": saritasa_invocations.Config(
            project_name="django-import-export-extensions",
            pre_commit=saritasa_invocations.PreCommitSettings(
                entry="prek",
                default_hook_stage="pre-push",
            ),
            celery=saritasa_invocations.CelerySettings(
                app="example.celery_app:app",
                scheduler="",
                extra_params=("",),
            ),
            django=saritasa_invocations.DjangoSettings(
                manage_file_path="example/manage.py",
                settings_path="example.settings",
                apps_path="example",
            ),
            github_actions=saritasa_invocations.GitHubActionsSettings(
                hosts=("postgres", "redis"),
            ),
        ),
    },
)
