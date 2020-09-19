#!/usr/bin/env python
from __future__ import unicode_literals

import os
from setuptools import setup

try:
    README = open(os.path.join(os.path.dirname(__file__), 'README.md')).read()
except IOError:
    README = ''

setup(
    name='redmine-gitlab-migrator',
    version='1.0.3',
    description='Migrate a redmine project to gitlab',
    long_description=README,
    author='Jocelyn Delalande',
    author_email='jdelalande@oasiswork.fr',
    license='GPL',
    url='https://github.com/redmine-gitlab-migrator/redmine-gitlab-migrator',
    packages=['redmine_gitlab_migrator'],
    install_requires=['pyyaml', 'requests', 'GitPython', 'pypandoc'],
    entry_points={
        'console_scripts': [
            'migrate-rg = redmine_gitlab_migrator.commands:main'
        ]
    },
    test_suite='redmine_gitlab_migrator.tests',
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)'
    ]
)
