#!/usr/bin/env python

"""The setup script."""

import os

from setuptools import find_packages, setup

with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()

def strip_comments(line: str) -> str:
    """Remove comment from the line."""
    return line.split("#", 1)[0].strip()


def _pip_requirement(req: str) -> list[str]:
    """Handle requirements from files with `-r` key."""
    if req.startswith("-r "):
        _, path = req.split()
        return reqs(*path.split("/"))
    return [req]


def _reqs(file_name: str) -> list[list[str]]:
    """Handle requirements from other files and remove comments."""
    return [
        _pip_requirement(req) for req in (
            strip_comments(line) for line in open(
                os.path.join(os.getcwd(), "requirements", file_name),
            ).readlines()
        ) if req
    ]


def reqs(file_name: str) -> list[str]:
    """Get requirements list."""
    return [req for subreq in _reqs(file_name) for req in subreq]


setup(
    author="Saritasa",
    author_email="pypi@saritasa.com",
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Framework :: Django",
        "Framework :: Django :: 3.2",
        "Framework :: Django :: 4.0",
        "Framework :: Django :: 4.1",
        "Framework :: Django :: 4.2",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    description="TODO: There should be description\nTODO: Rename project",
    entry_points={
        "console_scripts": [
            "import_export_extensions=import_export_extensions.cli:main",
        ],
    },
    install_requires=reqs("production.txt"),
    license="MIT license",
    long_description=readme + "\n\n" + history,
    include_package_data=True,
    keywords="import_export_extensions",
    name="import_export_extensions",
    packages=find_packages(include=["import_export_extensions", "import_export_extensions.*"]),
    test_suite="tests",
    tests_require=reqs("development.txt"),
    url="https://github.com/saritasa-nest/django-import-export-extensions",
    version="0.1.0",
    zip_safe=False,
)
