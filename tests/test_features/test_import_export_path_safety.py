"""Tests for import_export path traversal prevention."""

import json

import pytest

from features.import_export import ImportExport


@pytest.fixture
def ie(tmp_path):
    """Create ImportExport with controlled export_dir."""
    export_dir = tmp_path / "exports"
    export_dir.mkdir()

    class FakeCM:
        def __init__(self, base):
            self._base = base

        @property
        def base_dir(self):
            return self._base

    obj = ImportExport.__new__(ImportExport)
    obj._cm = FakeCM(tmp_path)
    obj.export_dir = export_dir
    return obj


def test_import_rejects_traversal(ie):
    with pytest.raises(ValueError, match="escapes base directory"):
        import asyncio

        asyncio.run(ie.import_user("../../etc/passwd"))


def test_import_rejects_absolute_path(ie):
    with pytest.raises(ValueError, match="escapes base directory"):
        import asyncio

        asyncio.run(ie.import_user("/etc/passwd"))


def test_import_accepts_valid_file(ie):
    """Valid file in export_dir should be accepted (may fail on DB, but path check passes)."""
    export_file = ie.export_dir / "valid_export.json"
    export_file.write_text(
        json.dumps(
            {
                "user_id": "test_user",
                "core_memory": [],
                "episodes": [],
            }
        ),
        encoding="utf-8",
    )

    import asyncio

    # This will fail at the DB level (FakeCM has no get), but path validation passes
    try:
        asyncio.run(ie.import_user(str(export_file)))
    except AttributeError:
        pass  # Expected — FakeCM doesn't have get()
