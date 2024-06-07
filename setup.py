#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name='bundleutilspkg',
    version='0.1',
    packages=find_packages(),
    package_data={
        'bundleutilspkg': ['configs/*.yaml'],
    },
    install_requires=[
        'click',
        'glob2',
        'ruamel.yaml',
        'ruamel.yaml.clib',
        'deepdiff',
        'requests',
        'jsonpatch',
    ],
    entry_points={
        'console_scripts': [
            'bundleutils = bundleutilspkg.scripts.bundleutils:cli',
        ],
    },
)