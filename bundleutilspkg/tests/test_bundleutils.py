import pytest
import os
import ruamel.yaml
from click.testing import CliRunner
from scripts.bundleutils import bundleutils

@pytest.fixture
def runner():
    return CliRunner()

def test_hello_command(runner):
    result = runner.invoke(bundleutils, [])
    assert result.exit_code == 0
    assert "Usage: bundleutils [OPTIONS]" in result.output

def test_hello_command_missing_argument(runner):
    result = runner.invoke(bundleutils, ["completion"])
    assert result.exit_code != 0  # Click should return an error
    assert "Missing option '-s'" in result.output