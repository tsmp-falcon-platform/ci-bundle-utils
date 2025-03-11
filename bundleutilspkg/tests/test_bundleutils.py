import pytest
import os
import ruamel.yaml
import shutil
from click.testing import CliRunner
from bundleutilspkg.bundleutils import bundleutils

yaml = ruamel.yaml.YAML(typ="rt")

@pytest.fixture
def runner():
    return CliRunner()

def test_usage(runner):
    result = runner.invoke(bundleutils, [])
    assert result.exit_code == 0
    assert "Usage: bundleutils [OPTIONS]" in result.output

def test_completion_missing_argument(runner):
    result = runner.invoke(bundleutils, ["completion"])
    assert result.exit_code != 0  # Click should return an error
    assert "Missing option '-s'" in result.output

def _test_merge_bundles(testdir, test_name, runner, command_args, expected_dir):
    outdir = os.path.join(testdir, 'resources', 'target', test_name)
    assert outdir.endswith(f'tests/resources/target/{test_name}')
    # delete the output directory recursively if it exists
    shutil.rmtree(outdir, ignore_errors=True)
    os.makedirs(outdir, exist_ok=True)
    result = runner.invoke(bundleutils, command_args)
    assert result.exit_code == 0
    assert os.path.exists(os.path.join(outdir, 'bundle.yaml'))
    # compare the yaml files in the output directory with the equivalent yaml files in the expected directory
    expected_dir = os.path.join(os.path.dirname(__file__), expected_dir)
    for file in os.listdir(outdir):
        # ignore the bundle.yaml file
        if file == 'bundle.yaml':
            continue
        with open(os.path.join(outdir, file), 'r') as f:
            outdata = yaml.load(f)
        with open(os.path.join(expected_dir, file), 'r') as f:
            expected_data = yaml.load(f)
        assert outdata == expected_data


def test_merge_bundles_base_only(request, runner):
    testdir = os.path.dirname(__file__)
    test_name = request.node.name
    outdir = os.path.join(testdir, 'resources', 'target', test_name)
    expected_dir = 'resources/merge-bundles/base-expected'
    command_args = ["merge-bundles",
                    "-b", f"{testdir}/resources/merge-bundles/base",
                    "-o", outdir]
    _test_merge_bundles(testdir, test_name, runner, command_args, expected_dir)

def test_merge_bundles_base_child(request, runner):
    testdir = os.path.dirname(__file__)
    test_name = request.node.name
    outdir = os.path.join(testdir, 'resources', 'target', test_name)
    expected_dir = 'resources/merge-bundles/base-child1-expected'
    command_args = ["merge-bundles",
                    "-b", f"{testdir}/resources/merge-bundles/base",
                    "-b", f"{testdir}/resources/merge-bundles/child1",
                    "-o", outdir]
    _test_merge_bundles(testdir, test_name, runner, command_args, expected_dir)

def test_merge_bundles_base_child_grandchild(request, runner):
    testdir = os.path.dirname(__file__)
    test_name = request.node.name
    outdir = os.path.join(testdir, 'resources', 'target', test_name)
    expected_dir = 'resources/merge-bundles/base-child1-grandchild1-expected'
    command_args = ["merge-bundles",
                    "-b", f"{testdir}/resources/merge-bundles/base",
                    "-b", f"{testdir}/resources/merge-bundles/child1",
                    "-b", f"{testdir}/resources/merge-bundles/grandchild1",
                    "-o", outdir]
    _test_merge_bundles(testdir, test_name, runner, command_args, expected_dir)

