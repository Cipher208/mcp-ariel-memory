"""Tests for backup path traversal prevention."""

import json

import pytest

from features.backup import BackupManager


@pytest.fixture
def bm(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return BackupManager(base_dir=str(data_dir))


def test_restore_rejects_traversal_in_manifest(bm):
    """Crafted manifest with ../../ in filenames should be rejected."""
    # Create a malicious backup directory with crafted manifest
    backup_dir = bm.backup_dir / "malicious"
    backup_dir.mkdir()
    manifest = {
        "files": ["../../etc/crontab", "memory.db"],
        "created_at": "2026-01-01T00:00:00",
    }
    (backup_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    import asyncio

    with pytest.raises(ValueError, match="escapes base directory"):
        asyncio.run(bm.restore("malicious"))


def test_restore_rejects_absolute_path(bm):
    """Manifest with absolute path should be rejected."""
    backup_dir = bm.backup_dir / "absolute"
    backup_dir.mkdir()
    manifest = {
        "files": ["/etc/passwd"],
        "created_at": "2026-01-01T00:00:00",
    }
    (backup_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    import asyncio

    with pytest.raises(ValueError, match="escapes base directory"):
        asyncio.run(bm.restore("absolute"))


def test_restore_accepts_valid_files(bm):
    """Valid manifest with normal files should work."""
    # Create a real db file
    db_file = bm.base_dir / "memory.db"
    db_file.write_bytes(b"fake db")

    # Create a valid backup
    import asyncio

    asyncio.run(bm.backup("test_backup"))

    # Restore should work
    result = asyncio.run(bm.restore("test_backup"))
    assert "restored" in result
