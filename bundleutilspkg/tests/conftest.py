import pytest
import os
from copy import deepcopy

# Cache the original environment once
_original_env = None


@pytest.fixture(autouse=True)
def reset_env(monkeypatch):
    global _original_env

    # Capture the original env only once
    if _original_env is None:
        _original_env = deepcopy(os.environ)

    # Clear and reset everything before each test
    for key in list(os.environ.keys()):
        monkeypatch.delenv(key, raising=False)

    for key, value in _original_env.items():
        monkeypatch.setenv(key, value)
