#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name='bundle_utils',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click',
        'click_completion',
        'glob2',
        'ruamel.yaml',
        'ruamel.yaml.clib',
        'requests',
        'jsonpatch',
    ],
    entry_points='''
        [console_scripts]
        bundle_utils=bundle_utils.main:cli
    ''',
)