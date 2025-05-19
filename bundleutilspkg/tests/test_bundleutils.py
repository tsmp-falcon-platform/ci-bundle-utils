import traceback
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


def _traceback(result):
    if result.exception:
        traceback.print_exception(*result.exc_info)


def test_usage(runner):
    result = runner.invoke(bundleutils, [])
    assert result.exit_code == 0
    _traceback(result)
    assert "Usage: bundleutils [OPTIONS]" in result.output


def test_completion_missing_argument(runner):
    result = runner.invoke(bundleutils, ["completion"])
    _traceback(result)
    assert result.exit_code != 0  # Click should return an error
    assert "Missing option '-s'" in result.output


def _test_diff(runner, src1, src2, exit_code, text=None):
    testdir = os.path.dirname(__file__)
    basedir = os.path.join(testdir, "resources", "merge-bundles")
    src1 = os.path.join(basedir, src1)
    src2 = os.path.join(basedir, src2)
    result = runner.invoke(bundleutils, ["diff", "-s", src1, "-s", src2])
    _traceback(result)
    assert result.exit_code == exit_code
    if exit_code != 0:
        assert text in result.output


def test_diff_file(runner):
    _test_diff(runner, "base/jenkins.yaml", "base/jenkins.yaml", 0)
    _test_diff(
        runner,
        "base/bundle.yaml",
        "base-expected/bundle.yaml",
        1,
        "Differences detected",
    )


def test_diff_directory(runner):
    _test_diff(runner, "base", "base", 0)
    _test_diff(runner, "base", "base-expected", 1, "Differences detected")


def _test_audit(testdir, test_name, runner, command_args, expected_dir):
    outdir = os.path.join(testdir, "resources", "target", test_name)
    assert outdir.endswith(f"tests/resources/target/{test_name}")
    # print out command and args for debugging
    print(f"Running command: bundleutils {' '.join(command_args)}")
    # delete the output directory recursively if it exists
    shutil.rmtree(outdir, ignore_errors=True)
    os.makedirs(outdir, exist_ok=True)
    result = runner.invoke(bundleutils, command_args)
    _traceback(result)
    assert result.exit_code == 0
    assert os.path.exists(os.path.join(outdir, "bundle.yaml"))
    # compare the yaml files in the output directory with the equivalent yaml files in the expected directory
    expected_dir = os.path.join(os.path.dirname(__file__), expected_dir)
    for file in os.listdir(outdir):
        with open(os.path.join(outdir, file), "r", encoding="utf-8") as f:
            outdata = yaml.load(f)
        with open(os.path.join(expected_dir, file), "r", encoding="utf-8") as f:
            expected_data = yaml.load(f)
        if file == "bundle.yaml":
            assert "parent" not in outdata.keys()
            assert outdata["version"] == expected_data["version"]
        else:
            assert outdata == expected_data


def _test_diff_19000(runner, command_args):
    # print out command and args for debugging
    print(f"Running command: bundleutils {' '.join(command_args)}")
    result = runner.invoke(bundleutils, command_args)
    _traceback(result)
    assert result.exit_code != 0
    assert '"new_value": "AUDITED_BUNDLE_DO_NOT_USE"' in result.output


def test_audit(request, runner):
    testdir = os.path.dirname(__file__)
    test_name = request.node.name
    outdir = os.path.join(testdir, "resources", "target", test_name)
    expected_dir = "resources/credentials/audit-expected"
    command_args = [
        "audit",
        "-s",
        f"{testdir}/resources/credentials/fetched-bundle",
        "-t",
        outdir,
    ]
    _test_audit(testdir, test_name, runner, command_args, expected_dir)


def test_performance_19000(request, runner):
    testdir = os.path.dirname(__file__)
    test_name = request.node.name
    outdir = os.path.join(testdir, "resources", "target", test_name)
    expected_dir = "resources/performance/lots-of-script-hashes-expected"
    command_args = [
        "audit",
        "-s",
        f"{testdir}/resources/performance/lots-of-script-hashes",
        "-t",
        outdir,
    ]
    _test_audit(testdir, test_name, runner, command_args, expected_dir)


def test_performance_diff_19000(request, runner):
    testdir = os.path.dirname(__file__)
    test_name = request.node.name
    expected_dir1 = os.path.join(testdir, "resources/performance/lots-of-script-hashes")
    expected_dir2 = os.path.join(
        testdir, "resources/performance/lots-of-script-hashes-expected"
    )
    command_args = [
        "diff",
        "-s",
        expected_dir1,
        "-s",
        expected_dir2,
    ]
    _test_diff_19000(runner, command_args)


def test_audit_no_hash(request, runner):
    testdir = os.path.dirname(__file__)
    test_name = request.node.name
    outdir = os.path.join(testdir, "resources", "target", test_name)
    expected_dir = "resources/credentials/audit-no-hash-expected"
    command_args = [
        "audit",
        "-s",
        f"{testdir}/resources/credentials/fetched-bundle",
        "-t",
        outdir,
        "--no-hash",
    ]
    _test_audit(testdir, test_name, runner, command_args, expected_dir)


def _test_merge_bundles(testdir, test_name, runner, command_args, expected_dir):
    outdir = os.path.join(testdir, "resources", "target", test_name)
    assert outdir.endswith(f"tests/resources/target/{test_name}")
    # print out command and args for debugging
    print(f"Running command: bundleutils {' '.join(command_args)}")
    # delete the output directory recursively if it exists
    shutil.rmtree(outdir, ignore_errors=True)
    os.makedirs(outdir, exist_ok=True)
    result = runner.invoke(bundleutils, command_args)
    _traceback(result)
    assert result.exit_code == 0
    assert os.path.exists(os.path.join(outdir, "bundle.yaml"))
    # compare the yaml files in the output directory with the equivalent yaml files in the expected directory
    expected_dir = os.path.join(os.path.dirname(__file__), expected_dir)
    for file in os.listdir(outdir):
        with open(os.path.join(outdir, file), "r", encoding="utf-8") as f:
            outdata = yaml.load(f)
        with open(os.path.join(expected_dir, file), "r", encoding="utf-8") as f:
            expected_data = yaml.load(f)
        if file == "bundle.yaml":
            assert "parent" not in outdata.keys()
            assert outdata["version"] == expected_data["version"]
        else:
            assert outdata == expected_data


def test_merge_bundles_base_only(request, runner):
    testdir = os.path.dirname(__file__)
    test_name = request.node.name
    outdir = os.path.join(testdir, "resources", "target", test_name)
    expected_dir = "resources/merge-bundles/base-expected"
    command_args = [
        "merge-bundles",
        "-b",
        f"{testdir}/resources/merge-bundles/base",
        "-o",
        outdir,
    ]
    _test_merge_bundles(testdir, test_name, runner, command_args, expected_dir)


def test_merge_bundles_base_child1(request, runner):
    testdir = os.path.dirname(__file__)
    test_name = request.node.name
    outdir = os.path.join(testdir, "resources", "target", test_name)
    expected_dir = "resources/merge-bundles/base-child1-expected"
    command_args = [
        "merge-bundles",
        "-b",
        f"{testdir}/resources/merge-bundles/base",
        "-b",
        f"{testdir}/resources/merge-bundles/child1",
        "-o",
        outdir,
    ]
    _test_merge_bundles(testdir, test_name, runner, command_args, expected_dir)


def test_merge_bundles_base_child1_grandchild1(request, runner):
    testdir = os.path.dirname(__file__)
    test_name = request.node.name
    outdir = os.path.join(testdir, "resources", "target", test_name)
    expected_dir = "resources/merge-bundles/base-child1-grandchild1-expected"
    command_args = [
        "merge-bundles",
        "-b",
        f"{testdir}/resources/merge-bundles/base",
        "-b",
        f"{testdir}/resources/merge-bundles/child1",
        "-b",
        f"{testdir}/resources/merge-bundles/grandchild1",
        "-o",
        outdir,
    ]
    _test_merge_bundles(testdir, test_name, runner, command_args, expected_dir)


def test_merge_bundles_use_parent_base_only(request, runner):
    testdir = os.path.dirname(__file__)
    test_name = request.node.name
    outdir = os.path.join(testdir, "resources", "target", test_name)
    expected_dir = "resources/merge-bundles-use-parent/base-expected"
    command_args = [
        "merge-bundles",
        "-b",
        f"{testdir}/resources/merge-bundles-use-parent/base",
        "-p",
        "-o",
        outdir,
    ]
    _test_merge_bundles(testdir, test_name, runner, command_args, expected_dir)


def test_merge_bundles_use_parent_base_child1(request, runner):
    testdir = os.path.dirname(__file__)
    test_name = request.node.name
    outdir = os.path.join(testdir, "resources", "target", test_name)
    expected_dir = "resources/merge-bundles-use-parent/base-child1-expected"
    command_args = [
        "merge-bundles",
        "-b",
        f"{testdir}/resources/merge-bundles-use-parent/child1",
        "-p",
        "-o",
        outdir,
    ]
    _test_merge_bundles(testdir, test_name, runner, command_args, expected_dir)


def test_merge_bundles_use_parent_base_child1_grandchild1(request, runner):
    testdir = os.path.dirname(__file__)
    test_name = request.node.name
    outdir = os.path.join(testdir, "resources", "target", test_name)
    expected_dir = "resources/merge-bundles-use-parent/base-child1-grandchild1-expected"
    command_args = [
        "merge-bundles",
        "-b",
        f"{testdir}/resources/merge-bundles-use-parent/grandchild1",
        "-p",
        "-o",
        outdir,
    ]
    _test_merge_bundles(testdir, test_name, runner, command_args, expected_dir)


def _test_fetch(testdir, test_name, runner, command_args, expected_strings):
    outdir = os.path.join(testdir, "resources", "target", test_name)
    assert outdir.endswith(f"tests/resources/target/{test_name}")
    # print out command and args for debugging
    print(f"Running command: bundleutils {' '.join(command_args)}")
    # delete the output directory recursively if it exists
    shutil.rmtree(outdir, ignore_errors=True)
    os.makedirs(outdir, exist_ok=True)
    result = runner.invoke(bundleutils, command_args)
    _traceback(result)
    assert result.exit_code == 0
    assert os.path.exists(os.path.join(outdir, "bundle.yaml"))
    assert os.path.exists(os.path.join(outdir, "jenkins.yaml"))
    # asssert expected_string is in the jenkins.yaml file
    with open(os.path.join(outdir, "jenkins.yaml"), "r", encoding="utf-8") as f:
        lines = f.readlines()
    for expected_string in expected_strings:
        found = False
        for line in lines:
            if expected_string in str(line):
                found = True
                break
            else:
                print(f"expected_string: {expected_string} not found in line: {line}")
        assert found


def test_fetch_default_keys_to_scalars(request, runner):
    testdir = os.path.dirname(__file__)
    test_name = request.node.name
    outdir = os.path.join(testdir, "resources", "target", test_name)
    expected_strings = ["  systemMessage: |", '  someCustomKey: "\\nCustom bla! \\n']
    command_args = [
        "fetch",
        "-P",
        f"{testdir}/resources/fetch/multiline-systemMessage.yaml",
        "-t",
        outdir,
    ]
    _test_fetch(testdir, test_name, runner, command_args, expected_strings)


def test_fetch_custom_keys_to_scalars(request, runner):
    testdir = os.path.dirname(__file__)
    test_name = request.node.name
    outdir = os.path.join(testdir, "resources", "target", test_name)
    expected_strings = [
        'systemMessage: "\\nHello People',
        "someCustomKey: |",
    ]
    command_args = [
        "fetch",
        "-P",
        f"{testdir}/resources/fetch/multiline-systemMessage.yaml",
        "-k",
        f"script,description,someCustomKey",
        "-t",
        outdir,
    ]
    _test_fetch(testdir, test_name, runner, command_args, expected_strings)


def test_fetch_add_missing_value(request, runner):
    testdir = os.path.dirname(__file__)
    test_name = request.node.name
    outdir = os.path.join(testdir, "resources", "target", test_name)
    expected_dir = "resources/fetch/missing-env-values-expected"
    command_args = [
        "fetch",
        "-P",
        f"{testdir}/resources/fetch/missing-env-values.yaml",
        "-t",
        outdir,
    ]
    _test_merge_bundles(testdir, test_name, runner, command_args, expected_dir)


def _test_transform(testdir, test_name, runner):
    # remove test_transform prefix from test_name and replace _ with -
    transform_config = f"transform/{test_name[15:].replace('_', '-')}"
    outdir = os.path.join(testdir, "resources", "target", test_name)
    expected_dir = f"resources/{transform_config}-expected"
    command_args = [
        "transform",
        "-s",
        f"{testdir}/resources/transform/base",
        "-c",
        f"{testdir}/resources/{transform_config}.yaml",
        "-t",
        outdir,
    ]
    _test_merge_bundles(testdir, test_name, runner, command_args, expected_dir)


def test_transform_using_wildcard_delete(request, runner):
    testdir = os.path.dirname(__file__)
    test_name = request.node.name
    _test_transform(testdir, test_name, runner)


def test_transform_using_selectors_jenkins_1(request, runner):
    testdir = os.path.dirname(__file__)
    test_name = request.node.name
    _test_transform(testdir, test_name, runner)


def test_transform_using_selectors_jenkins_2(request, runner):
    testdir = os.path.dirname(__file__)
    test_name = request.node.name
    _test_transform(testdir, test_name, runner)


def test_transform_using_selectors_items(request, runner):
    testdir = os.path.dirname(__file__)
    test_name = request.node.name
    _test_transform(testdir, test_name, runner)


def _test_extract_from_pattern(runner, string, pattern, expected_output, exit_code=0):
    command_args = ["extract-from-pattern", "-s", string]
    if pattern:
        command_args += ["-p", pattern]
    print(f"Running command: bundleutils {' '.join(command_args)}")
    result = runner.invoke(bundleutils, command_args)
    _traceback(result)
    assert result.exit_code == exit_code
    assert expected_output in result.output


def test_extract_from_pattern_default_pattern(runner):
    string = "main-controller-name-drift"
    expected_output = "controller-name"
    _test_extract_from_pattern(runner, string, None, expected_output)


def test_extract_from_pattern_full_string(runner):
    string = "controller-name"
    pattern = r"^([a-z0-9\-]+)$"
    expected_output = "controller-name"
    _test_extract_from_pattern(runner, string, pattern, expected_output)


def test_extract_from_pattern_prefix_suffix(runner):
    string = "main-controller-name-drift"
    pattern = r"^main-([a-z0-9\-]+)-drift$"
    expected_output = "controller-name"
    _test_extract_from_pattern(runner, string, pattern, expected_output)


def test_extract_from_pattern_prefix_only(runner):
    string = "feature/testing-controller-name"
    pattern = r"^feature/testing-([a-z0-9\-]+)$"
    expected_output = "controller-name"
    _test_extract_from_pattern(runner, string, pattern, expected_output)


def test_extract_from_pattern_prefix_suffix_optional(runner):
    string = "feature/JIRA-1234/controller-name__something"
    pattern = r"^feature/[A-Z]+-\d+/([a-z0-9\-]+)(?:__[a-z0-9\-]+)*$"
    expected_output = "controller-name"
    _test_extract_from_pattern(runner, string, pattern, expected_output)


def test_extract_from_pattern_invalid_string(runner):
    string = "invalid-string"
    pattern = r"^main-([a-z0-9\-]+)-drift$"
    expected_output = "No match found"
    _test_extract_from_pattern(runner, string, pattern, expected_output, exit_code=1)


def test_extract_from_pattern_missing_pattern(runner):
    command_args = ["extract-from-pattern"]
    result = runner.invoke(bundleutils, command_args)
    _traceback(result)
    assert result.exit_code != 0
    assert "Error: Missing option '-s'" in result.output


def test_extract_from_pattern_env_var(runner, monkeypatch):
    string = "feature/testing-controller-name"
    pattern = r"^feature/testing-([a-z0-9\-]+)$"
    expected_output = "controller-name"
    monkeypatch.setenv("BUNDLEUTILS_BUNDLES_PATTERN", pattern)
    _test_extract_from_pattern(runner, string, pattern, expected_output)
