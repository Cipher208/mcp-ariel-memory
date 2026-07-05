"""Tests for shared/migrations.py — full coverage."""

import asyncio
import pytest
from shared.migrations import MigrationManager


@pytest.fixture
def mm(tmp_path):
    from shared.connection import AsyncConnectionManager
    cm = AsyncConnectionManager(base_dir=str(tmp_path))
    return MigrationManager(cm=cm)


def test_get_current_version_empty(mm):
    """get_current_version should return 0 for empty DB."""
    async def t():
        version = await mm.get_current_version()
        assert version == 0
    asyncio.run(t())


def test_migrate_runs(mm):
    """migrate should run without error."""
    async def t():
        result = await mm.migrate()
        assert isinstance(result, dict)
        assert "applied" in result
        assert len(result["applied"]) > 0
    asyncio.run(t())


def test_migrate_idempotent(mm):
    """Running migrate twice should not re-apply."""
    async def t():
        r1 = await mm.migrate()
        r2 = await mm.migrate()
        assert len(r2["applied"]) == 0  # No new migrations
        assert r2["current_version"] == r1["new_version"]
    asyncio.run(t())


def test_get_pending(mm):
    """get_pending should return pending migrations."""
    async def t():
        pending = await mm.get_pending()
        assert isinstance(pending, list)
        # After migrate, no pending
        await mm.migrate()
        pending_after = await mm.get_pending()
        assert len(pending_after) == 0
    asyncio.run(t())


def test_migrate_returns_version_info(mm):
    """migrate should return version info."""
    async def t():
        result = await mm.migrate()
        assert "current_version" in result
        assert "new_version" in result
        assert result["new_version"] >= result["current_version"]
    asyncio.run(t())


def test_get_current_version_after_migrate(mm):
    """get_current_version should return correct version after migrate."""
    async def t():
        await mm.migrate()
        version = await mm.get_current_version()
        assert version > 0
    asyncio.run(t())
