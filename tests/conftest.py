"""Shared fixtures for all tests."""

import gc
import os

# Disable backup_cron before any imports to prevent daemon threads
os.environ["BACKUP_CRON_DISABLED"] = "1"

import pytest


@pytest.fixture(autouse=True, scope="session")
def master_key_env():
    """Set master key for encryption across all tests."""
    os.environ["MCP_MASTER_KEY"] = "test-secret-for-unit-tests-only"
    from features import secrets
    secrets._master_cache.clear()
    yield
    os.environ.pop("MCP_MASTER_KEY", None)
    gc.collect()


@pytest.fixture(scope="session", autouse=True)
async def cleanup_db_connections():
    """Guarantee all aiosqlite engines are closed before session ends."""
    yield
    try:
        from shared.connection import connection_manager
        for name, conn in list(connection_manager._conns.items()):
            try:
                if hasattr(conn, '_conn') and hasattr(conn._conn, 'close'):
                    conn._conn.close()
            except Exception:
                pass
        connection_manager._conns.clear()
    except Exception:
        pass
