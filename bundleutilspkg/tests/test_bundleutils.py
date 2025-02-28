import pytest
import os
import ruamel.yaml
import shutil
from click.testing import CliRunner
from scripts.bundleutils import bundleutils

yaml = ruamel.yaml.YAML(typ="rt")

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

def test_merge_bundles_1(request, runner):
    testdir = os.path.dirname(__file__)
    outdir = os.path.join(testdir, 'resources', 'target', request.node.name)
    assert outdir == '/home/sboardwell/Workspace/tsmp-falcon-platform/ci-bundle-utils/bundleutilspkg/tests/resources/target/test_merge_bundles_1'
    # delete the output directory recursively if it exists
    shutil.rmtree(outdir, ignore_errors=True)
    os.makedirs(outdir, exist_ok=True)
    result = runner.invoke(bundleutils, ["merge-bundles", "-b", f"{testdir}/resources/merge-bundles/base", "-b", f"{testdir}/resources/merge-bundles/child1", "-o", outdir])
    assert result.exit_code == 0
    assert os.path.exists(os.path.join(outdir, 'bundle.yaml'))
    # compare the yaml files in the output directory with the equivalent yaml files in the expected directory
    expected_dir = os.path.join(os.path.dirname(__file__), 'resources/merge-bundles/base-child1-expected')
    for file in os.listdir(outdir):
        # ignore the bundle.yaml file
        if file == 'bundle.yaml':
            continue
        with open(os.path.join(outdir, file), 'r') as f:
            outdata = yaml.load(f)
        with open(os.path.join(expected_dir, file), 'r') as f:
            expected_data = yaml.load(f)
        assert outdata == expected_data
