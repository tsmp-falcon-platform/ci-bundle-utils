import ruamel.yaml
import pytest
import traceback
from bundleutilspkg.bundleutils import _get_merged_config

yaml = ruamel.yaml.YAML(typ="rt")


class DummyDie(Exception):
    pass


def die(msg):
    raise DummyDie(msg)


@pytest.fixture(autouse=True)
def patch_die(monkeypatch):
    # Patch die in the tested module to raise DummyDie for easier assertion
    import bundleutilspkg.bundleutils

    monkeypatch.setattr(bundleutilspkg.bundleutils, "die", die)


def _traceback(result):
    if hasattr(result, "exc_info") and result.exc_info:
        traceback.print_exception(*result.exc_info)


def write_yaml(path, data):
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f)


def test_get_merged_config_basic(tmp_path):
    config = {"foo": "bar"}
    config_path = tmp_path / "config.yaml"
    write_yaml(config_path, config)
    result = _get_merged_config(str(config_path))
    _traceback(result)
    assert result == config


def test_get_merged_config_missing_file(tmp_path):
    missing_path = tmp_path / "missing.yaml"
    with pytest.raises(DummyDie) as exc:
        _get_merged_config(str(missing_path))
    assert "does not exist" in str(exc.value)


def test_get_merged_config_not_a_file(tmp_path):
    # Create a directory instead of a file
    dir_path = tmp_path / "adir"
    dir_path.mkdir()
    with pytest.raises(DummyDie) as exc:
        _get_merged_config(str(dir_path))
    assert "is not a file" in str(exc.value)


def test_get_merged_config_empty_file(tmp_path):
    config_path = tmp_path / "empty.yaml"
    config_path.write_text("")
    with pytest.raises(DummyDie) as exc:
        _get_merged_config(str(config_path))
    assert "empty or invalid YAML" in str(exc.value)


def test_get_merged_config_includes(tmp_path):
    # Create base config with includes
    base = {"foo": "bar", "includes": "child.yaml"}
    child = {"baz": "qux"}
    base_path = tmp_path / "base.yaml"
    child_path = tmp_path / "child.yaml"
    write_yaml(base_path, base)
    write_yaml(child_path, child)
    result = _get_merged_config(str(base_path))
    _traceback(result)
    # Should merge child into base, and remove 'includes'
    assert result["foo"] == "bar"
    assert result["baz"] == "qux"
    assert "includes" not in result


def test_get_merged_config_includes_list(tmp_path):
    # Create base config with multiple includes
    base = {"foo": "bar", "includes": ["child1.yaml", "child2.yaml"]}
    child1 = {"baz": "qux"}
    child2 = {"hello": "world"}
    base_path = tmp_path / "base.yaml"
    child1_path = tmp_path / "child1.yaml"
    child2_path = tmp_path / "child2.yaml"
    write_yaml(base_path, base)
    write_yaml(child1_path, child1)
    write_yaml(child2_path, child2)
    result = _get_merged_config(str(base_path))
    _traceback(result)
    assert result["foo"] == "bar"
    assert result["baz"] == "qux"
    assert result["hello"] == "world"
    assert "includes" not in result


def test_get_merged_config_includes_missing(tmp_path):
    base = {"foo": "bar", "includes": "missing.yaml"}
    base_path = tmp_path / "base.yaml"
    write_yaml(base_path, base)
    with pytest.raises(DummyDie) as exc:
        _get_merged_config(str(base_path))
    assert "Included config file" in str(exc.value)


def test_get_merged_config_recursive_includes(tmp_path):
    # base includes child, child includes grandchild
    base = {"foo": "bar", "includes": "child.yaml"}
    child = {"baz": "qux", "includes": "grandchild.yaml"}
    grandchild = {"hello": "world"}
    base_path = tmp_path / "base.yaml"
    child_path = tmp_path / "child.yaml"
    grandchild_path = tmp_path / "grandchild.yaml"
    write_yaml(base_path, base)
    write_yaml(child_path, child)
    write_yaml(grandchild_path, grandchild)
    result = _get_merged_config(str(base_path))
    _traceback(result)
    assert result["foo"] == "bar"
    assert result["baz"] == "qux"
    assert result["hello"] == "world"
    assert "includes" not in result


def test_get_merged_config_none_config():
    with pytest.raises(DummyDie) as exc:
        _get_merged_config(None)
    assert "No transformation config" in str(exc.value)
