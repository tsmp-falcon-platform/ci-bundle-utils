#!/usr/bin/env python
from setuptools import setup, find_packages
import subprocess
import os
def get_version():
    """Determine the application version."""
    # Check if BUNDLEUTILS_RELEASE_VERSION and BUNDLEUTILS_RELEASE_HASH are provided as environment variables
    release_version = os.getenv("BUNDLEUTILS_RELEASE_VERSION")
    release_hash = os.getenv("BUNDLEUTILS_RELEASE_HASH")

    if release_version and release_hash:
        return release_version, release_hash

    # Fallback to Git information if environment variable is not set
    try:
        release_version = subprocess.check_output(["git", "describe", "--tags"], text=True).strip()
        release_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        return release_version, release_hash
    except Exception:
        return "0.0.0", "unknown"

# Retrieve Git metadata
release_version, release_hash = get_version()

# Package description
description = f"{release_version} (built from {release_hash})"

setup(
    name='bundleutilspkg',
    version=release_version,
    description=description,
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