import os
import subprocess
import re

def get_version():
    """Determine the application version."""
    release_version = os.getenv("BUNDLEUTILS_RELEASE_VERSION")
    release_hash = os.getenv("BUNDLEUTILS_RELEASE_HASH")

    if not (release_version and release_hash):
        try:
            release_version = subprocess.check_output(["git", "describe", "--tags"], text=True).strip()
            release_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        except Exception:
            release_version = "0.0.0"
            release_hash = "unknown"

    # Convert 'v0.5.14-9-g956417c' -> '0.5.14.dev9+g956417c'
    match = re.match(r"v?(\d+\.\d+\.\d+)-(\d+)-g([0-9a-f]+)", release_version)
    if match:
        release_version = f"{match.group(1)}.dev{match.group(2)}+{match.group(3)}"

    return release_version, release_hash

release_version, release_hash = get_version()
__version__ = release_version
__description__ = f"{release_version} (built from {release_hash})"