import os
import ruamel.yaml
import pytest
from bundle_renderer.yaml_merger import YAMLMerger

yaml = ruamel.yaml.YAML(typ="rt")

@pytest.fixture
def merger():
    return YAMLMerger()

@pytest.fixture
def test_dir():
    return os.path.join(os.path.dirname(__file__), 'resources')

def _test_merge_yaml_files(merger, test_dir, expected_file, *files):
    expected_file = os.path.join(test_dir, expected_file)
    files = [os.path.join(test_dir, file) for file in files]
    merged_data = merger.merge_yaml_files(files)
    with open(expected_file, 'r') as f:
        expected_data = yaml.load(f)
    assert merged_data == expected_data

def test_merge_yaml_files(merger, test_dir):
    _test_merge_yaml_files(merger, test_dir, 'expected.yaml', 'parent.yaml', 'child.yaml')

def test_merge_yaml_files_no_child(merger, test_dir):
    _test_merge_yaml_files(merger, test_dir, 'parent.yaml', 'parent.yaml')

def test_merge_yaml_plugin_files_parent(merger, test_dir):
    _test_merge_yaml_files(merger, test_dir, 'plugins/expected-parent.yaml', 'plugins/parent.yaml')

def test_merge_yaml_plugin_files_child(merger, test_dir):
    _test_merge_yaml_files(merger, test_dir, 'plugins/expected-parent-child.yaml', 'plugins/parent.yaml', 'plugins/child.yaml')

def test_merge_yaml_plugin_files_grandchild(merger, test_dir):
    _test_merge_yaml_files(merger, test_dir, 'plugins/expected-parent-child-grandchild.yaml', 'plugins/parent.yaml', 'plugins/child.yaml', 'plugins/grandchild.yaml')
