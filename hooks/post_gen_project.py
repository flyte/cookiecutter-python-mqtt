#!/usr/bin/env python
import os

import travis_pypi_setup


PROJECT_DIRECTORY = os.path.realpath(os.path.curdir)


def remove_file(filepath):
    os.remove(os.path.join(PROJECT_DIRECTORY, filepath))


if __name__ == '__main__':
    args = object()
    args.repo = "{{ cookiecutter.github_username }}/{{ cookiecutter.project_slug.replace('_', '-') }}"
    travis_pypi_setup.main(args)
    remove_file('travis_pypi_setup.py')
