"""Tests for unified ops tools (tools_ops.py)."""

import pytest


@pytest.fixture(autouse=True)
def setup_master_key(monkeypatch):
    monkeypatch.setenv("MCP_MASTER_KEY", "test-secret-for-unit-tests-only")
    from features import secrets

    secrets._master_cache.clear()


def test_api_key_create():
    from features.auth import api_key_auth

    key = api_key_auth.create_key("test_user", "test_label")
    assert key.startswith("ak_")
    assert len(key) > 20


def test_api_key_list():
    from features.auth import api_key_auth

    api_key_auth.create_key("test_user", "list_test")
    keys = api_key_auth.list_keys()
    assert len(keys) >= 1


def test_api_key_revoke():
    from features.auth import api_key_auth

    key = api_key_auth.create_key("test_user", "revoke_test")
    revoked = api_key_auth.revoke(key)
    assert revoked is True


def test_backup_status():
    from features.backup_cron import backup_cron

    status = backup_cron.status()
    assert "running" in status
    assert "interval_hours" in status


def test_saga_consolidate():
    from shared.saga import create_consolidation_saga

    from core import MemoryManager
    from shared.cache import MemoryCache

    mm = MemoryManager(cache=MemoryCache())
    saga = create_consolidation_saga("test_user", mm=mm)
    assert saga is not None
    assert "consolidation" in saga.name


def test_saga_backup():
    from shared.saga import create_backup_saga

    saga = create_backup_saga()
    assert saga is not None
    assert saga.name == "backup"


def test_data_list_exports(tmp_path):
    from features.import_export import ImportExport

    from shared.connection import AsyncConnectionManager

    cm = AsyncConnectionManager(base_dir=str(tmp_path))
    ie = ImportExport(cm=cm)
    exports = ie.list_exports()
    assert isinstance(exports, list)


def test_cleanup():
    from features.compression import MemoryCompressor

    mc = MemoryCompressor()
    assert mc is not None
