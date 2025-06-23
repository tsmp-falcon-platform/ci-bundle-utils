import ruamel.yaml
import pytest
import traceback
from bundleutilspkg.bundleutils import remove_files_from_dir

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


def test_remove_files_from_dir(tmp_path):
    # Create some test files
    file1 = tmp_path / "file1.txt"

    file1.write_text("Content of file 1")

    # Call the function to remove files
    # Expect an exception since tmp_dir is not with a "target" directory
    with pytest.raises(DummyDie) as exc:
        result = remove_files_from_dir(str(tmp_path))
        _traceback(result)
    assert "does not have a 'target' directory in its path" in str(exc.value)
    assert file1.exists()


def test_remove_files_from_dir_with_target(tmp_path):
    # Create a target directory and some test files
    target_dir = tmp_path / "target" / "subdir"
    target_dir.mkdir(parents=True)
    file1 = target_dir / "file1.txt"
    file2 = target_dir / "file2.txt"

    file1.write_text("Content of file 1")
    file2.write_text("Content of file 2")

    # Call the function to remove files
    result = remove_files_from_dir(str(target_dir))
    _traceback(result)

    # Check that the files were removed
    assert not file1.exists()
    assert not file2.exists()


def test_remove_files_from_dir_1_level_of_sub_directory(tmp_path):
    # Create a target directory with more than 2 levels of subdirectories
    target_dir = tmp_path / "target" / "subdir"
    extra_dirs = target_dir / "subdir1"
    extra_dirs.mkdir(parents=True)
    file1 = extra_dirs / "file1.txt"

    file1.write_text("Content of file 1")

    # Call the function to remove files
    result = remove_files_from_dir(str(target_dir))
    _traceback(result)

    # Check that the files were removed
    assert not file1.exists()


def test_remove_files_from_dir_more_than_2_levels_of_sub_directory(tmp_path):
    # Create a target directory with more than 2 levels of subdirectories
    target_dir = tmp_path / "target" / "subdir"
    extra_dirs = target_dir / "subdir1" / "subdir2"
    extra_dirs.mkdir(parents=True)
    file1 = extra_dirs / "file1.txt"

    file1.write_text("Content of file 1")

    # Call the function to remove files
    # Expect an exception since tmp_dir is not with a "target" directory
    with pytest.raises(DummyDie) as exc:
        result = remove_files_from_dir(str(target_dir))
        _traceback(result)
    assert "levels, which is more than the allowed maximum" in str(exc.value)
    assert file1.exists()
