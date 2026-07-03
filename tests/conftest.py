"""Shared fixtures for all tests."""

import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def master_key_env():
    """Set master key for encryption across all tests."""
    os.environ["MCP_MASTER_KEY"] = "test-secret-for-unit-tests-only"
    os.environ["BACKUP_CRON_DISABLED"] = "1"
    from features import secrets

    secrets._master_cache.clear()
    yield
    os.environ.pop("MCP_MASTER_KEY", None)
    os.environ.pop("BACKUP_CRON_DISABLED", None)
