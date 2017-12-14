#!/usr/bin/env python
import os

from .travis_pypi_setup import main as setup_pypi_travis


PROJECT_DIRECTORY = os.path.realpath(os.path.curdir)


def remove_file(filepath):
    os.remove(os.path.join(PROJECT_DIRECTORY, filepath))


if __name__ == '__main__':
    args = object()
    args.repo = "{{ cookiecutter.github_username }}/{{ cookiecutter.project_slug.replace('_', '-') }}"
    setup_pypi_travis(args)
    remove_file('travis_pypi_setup.py')
