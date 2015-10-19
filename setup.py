#!/usr/bin/env python
from __future__ import unicode_literals

import os
from setuptools import setup

README = open(os.path.join(os.path.dirname(__file__), 'README.md')).read()

setup(name='migrate-redmine-to-gitlab',
      version='0.1',
      description='Migrate a redmine project to gitlab',
      long_description=README,
      author='Jocelyn Delalande',
      author_email='jdelalande@oasiswork.fr',
      url='https://github/oasiswork/migrate-redmine-to-gitlab/',
      packages=['redmine_gitlab_migrator'],
      install_requires=['requests'],
      scripts=['scripts/migrate-gitlab-to-redmine']
      )
