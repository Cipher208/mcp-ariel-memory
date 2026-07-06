"""Tests for shared.path_safety — path traversal prevention."""

import pytest

from shared.path_safety import safe_resolve


def test_safe_resolve_realpath_within_base(tmp_path):
    sub = tmp_path / "allowed"
    sub.mkdir()
    result = safe_resolve(tmp_path, "allowed")
    assert result.resolve() == sub.resolve()


def test_safe_resolve_symlink_escape_raises(tmp_path):
    link = tmp_path / "escape"
    link.symlink_to("/etc")
    with pytest.raises(ValueError, match="escapes base directory"):
        safe_resolve(tmp_path, "escape/passwd")


def test_safe_resolve_dot_dot_within_base(tmp_path):
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    result = safe_resolve(tmp_path, "a/b/../b/file.txt")
    assert result.resolve() == (tmp_path / "a" / "b" / "file.txt").resolve()


def test_safe_resolve_empty_string(tmp_path):
    result = safe_resolve(tmp_path, "")
    assert result.resolve() == tmp_path.resolve()
