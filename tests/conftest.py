"""Shared fixtures for all tests."""

import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def master_key_env():
    """Set master key for encryption across all tests."""
    os.environ["MCP_MASTER_KEY"] = "test-secret-for-unit-tests-only"
    from features import secrets

    secrets._master_cache.clear()
    yield
    os.environ.pop("MCP_MASTER_KEY", None)
    # Stop backup_cron to prevent hanging threads
    try:
        from features.backup_cron import backup_cron

        backup_cron.stop()
    except Exception:
        pass
