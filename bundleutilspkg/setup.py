#!/usr/bin/env python
from setuptools import setup, find_packages
import subprocess
def get_git_info():
    """Retrieve the Git tag and commit hash."""
    # try:
    #     git_hash = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    #     return git_hash
    # except subprocess.CalledProcessError:
    return "0.0.0"  # Fallback for missing Git info

# Retrieve Git metadata
git_hash = get_git_info()

# Package description
description = f"MyApp - Commit: {git_hash}"

setup(
    name='bundleutilspkg',
    version=git_hash,
    description=description,
    long_description=f"This package was built from commit {git_hash}.",
    packages=find_packages(),
    package_data={
        'defaults': ['configs/**/*', 'configs/*'],
    },
    install_requires=[
        'click',
        'glob2',
        'ruamel.yaml',
        'ruamel.yaml.clib',
        'deepdiff',
        'requests',
        'jsonpatch',
        'packaging',
    ],
    entry_points={
        'console_scripts': [
            'bundleutils = scripts.bundleutils:cli',
        ],
    },
)