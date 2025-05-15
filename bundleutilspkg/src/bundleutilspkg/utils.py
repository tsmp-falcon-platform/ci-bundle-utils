import importlib
from pathlib import Path
import sys


def get_config_file(filename):
    """Load a YAML config file from bundleutilspkg.data.configs."""
    if getattr(sys, "frozen", False):  # PyInstaller build
        base_path = Path(sys._MEIPASS) / "data/configs"
    else:
        base_path = importlib.resources.files("bundleutilspkg.data.configs")

    return base_path / filename
