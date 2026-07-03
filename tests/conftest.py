"""Shared fixtures for all tests."""

import os
import sys

import pytest


@pytest.fixture(autouse=True, scope="session")
def master_key_env():
    """Set master key for encryption across all tests."""
    os.environ["MCP_MASTER_KEY"] = "test-secret-for-unit-tests-only"
    from features import secrets

    secrets._master_cache.clear()
    yield
    os.environ.pop("MCP_MASTER_KEY", None)
    # Force cleanup of all daemon threads to prevent CI hanging
    for thread in __import__("threading").enumerate():
        if thread.daemon and thread.is_alive() and thread != __import__("threading").main_thread():
            thread.join(timeout=1)
