from pathlib import Path

import pytest


def test_symlink_fixture_skips_only_windows_privilege_error(create_symlink):
    class FailingLink:
        def __init__(self, error):
            self.error = error

        def symlink_to(self, target, *, target_is_directory):
            raise self.error

    privilege_error = OSError("privilege not held")
    privilege_error.winerror = 1314
    with pytest.raises(pytest.skip.Exception, match="Windows privileges"):
        create_symlink(FailingLink(privilege_error), "target")

    other_error = OSError("different failure")
    with pytest.raises(OSError, match="different failure"):
        create_symlink(FailingLink(other_error), "target")


def test_symlink_fixture_leaves_path_method_unchanged(create_symlink, tmp_path):
    original = Path.symlink_to
    target = tmp_path / "target"
    target.write_bytes(b"data")
    link = tmp_path / "current"
    create_symlink(link, target)
    assert link.read_bytes() == b"data"
    assert Path.symlink_to is original
