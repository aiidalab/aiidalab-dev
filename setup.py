# -*- coding: utf8 -*-
"""Setting up base widgets for base package for AiiDA lab."""
import json

from setuptools import setup

with open('setup.json', 'r') as info:
    kwargs = json.load(info)  # pylint: disable=invalid-name

with open('requirements.txt', 'r') as rfile:
    requirements = rfile.read().splitlines()  # pylint: disable=invalid-name

# -i https://pypi.org/simple not supported in install_requires
if requirements[0].startswith('-i'):
    requirements.pop(0)

setup(long_description=open('README.md').read(),
      long_description_content_type='text/markdown',
      install_requires=requirements,
      entry_points={'console_scripts': ['develop-aiidalab = develop_aiidalab:cli']},
      **kwargs)
