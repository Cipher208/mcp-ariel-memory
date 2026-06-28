"""
Tests for auth, backup, import/export, and MCP auto-start.
"""

import pytest
import os


@pytest.fixture(autouse=True, scope="session")
def master_key_env():
    """Set master key for all tests."""
    os.environ["MCP_MASTER_KEY"] = "test-secret-for-unit-tests-only"
    from features import secrets

    secrets._master_cache.clear()
    yield
    os.environ.pop("MCP_MASTER_KEY", None)


# ═══════════════════════════════════════════════════════════════
# AUTH TESTS
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_api_key_create():
    from features.auth import APIKeyAuth

    auth = APIKeyAuth()
    key = auth.create_key("alice", "test key")
    assert key.startswith("ak_")
    assert len(key) > 20


@pytest.mark.asyncio
async def test_api_key_verify():
    from features.auth import APIKeyAuth

    auth = APIKeyAuth()
    key = auth.create_key("alice", "test key")
    info = auth.verify(key)
    assert info is not None
    assert info["user_id"] == "alice"
    assert info["label"] == "test key"


@pytest.mark.asyncio
async def test_api_key_revoke():
    from features.auth import APIKeyAuth

    auth = APIKeyAuth()
    key = auth.create_key("alice", "test key")
    assert auth.verify(key) is not None
    revoked = auth.revoke(key)
    assert revoked is True
    assert auth.verify(key) is None


@pytest.mark.asyncio
async def test_api_key_list():
    from features.auth import APIKeyAuth

    auth = APIKeyAuth()
    auth.create_key("alice", "key1")
    auth.create_key("alice", "key2")
    keys = auth.list_keys()
    assert len(keys) >= 2


@pytest.mark.asyncio
async def test_bearer_auth():
    from features.auth import BearerAuth

    ba = BearerAuth()
    token = ba.get_token()
    assert token.startswith("mt_")
    assert ba.verify("Bearer " + token) is True
    assert ba.verify("Bearer invalid") is False
    assert ba.verify("") is False


@pytest.mark.asyncio
async def test_bearer_rotate():
    from features.auth import BearerAuth

    ba = BearerAuth()
    old_token = ba.get_token()
    new_token = ba.rotate()
    assert old_token != new_token
    assert ba.verify("Bearer " + new_token) is True


# ═══════════════════════════════════════════════════════════════
# BACKUP TESTS
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_backup_create():
    from features.backup import BackupManager

    bm = BackupManager()
    path = await bm.backup(label="test_backup")
    assert path is not None
    assert os.path.exists(path)


@pytest.mark.asyncio
async def test_backup_list():
    from features.backup import BackupManager

    bm = BackupManager()
    await bm.backup(label="test_list")
    backups = bm.list_backups()
    assert len(backups) >= 1


@pytest.mark.asyncio
async def test_backup_restore():
    from features.backup import BackupManager

    bm = BackupManager()
    path = await bm.backup(label="test_restore")
    backup_name = os.path.basename(path)
    result = await bm.restore(backup_name)
    assert "restored" in result


@pytest.mark.asyncio
async def test_backup_cleanup():
    from features.backup import BackupManager

    bm = BackupManager()
    removed = bm.cleanup_old()
    assert isinstance(removed, int)


# ═══════════════════════════════════════════════════════════════
# IMPORT/EXPORT TESTS
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_export_import():
    from features.import_export import ImportExport
    from core import memory_manager

    # Create some data
    user = memory_manager.user_memory("export_test")
    await user.remember("key1", "value1", 0.8)

    ie = ImportExport()

    # Export
    export_path = await ie.export_user("export_test")
    assert export_path is not None
    assert os.path.exists(export_path)

    # List exports
    exports = ie.list_exports()
    assert len(exports) >= 1


# ═══════════════════════════════════════════════════════════════
# AUDIT TRAIL TESTS
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_audit_log():
    from features.audit_trail import AuditTrail

    at = AuditTrail()
    await at._init_db()
    await at.log("audit_test", "test_action", "user", "target_1", {"key": "value"})
    history = await at.get_history("audit_test")
    assert len(history) >= 1
    assert history[0]["action"] == "test_action"


@pytest.mark.asyncio
async def test_audit_count():
    from features.audit_trail import AuditTrail

    at = AuditTrail()
    await at._init_db()
    await at.log("count_test", "action1")
    await at.log("count_test", "action2")
    count = await at.count("count_test")
    assert count >= 2


@pytest.mark.asyncio
async def test_audit_cleanup():
    from features.audit_trail import AuditTrail

    at = AuditTrail()
    await at._init_db()
    removed = await at.cleanup_old(retention_days=0)
    assert isinstance(removed, int)


# ═══════════════════════════════════════════════════════════════
# RATE LIMITER TESTS
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_rate_limiter():
    from features.rate_limiting import RateLimiter

    rl = RateLimiter()
    result = await rl.check("rate_test")
    assert "allowed" in result
    assert result["allowed"] is True


@pytest.mark.asyncio
async def test_rate_limiter_stats():
    from features.rate_limiting import RateLimiter

    rl = RateLimiter()
    await rl.check("stats_test")
    stats = await rl.get_stats("stats_test")
    assert "requests_last_minute" in stats


# ═══════════════════════════════════════════════════════════════
# MCP AUTO-START TESTS
# ═══════════════════════════════════════════════════════════════


def test_mcp_tools_count():
    from mcp_server import mcp

    tools = mcp._tool_manager.list_tools()
    assert len(tools) >= 37


def test_mcp_tools_are_async():
    import inspect
    from mcp_server import (
        memory_user_remember,
        memory_agent_remember,
        memory_backup_now,
        memory_create_api_key,
        memory_lucidity_purge,
        memory_search_rrf,
    )

    assert inspect.iscoroutinefunction(memory_user_remember)
    assert inspect.iscoroutinefunction(memory_agent_remember)
    assert inspect.iscoroutinefunction(memory_backup_now)
    assert inspect.iscoroutinefunction(memory_create_api_key)
    assert inspect.iscoroutinefunction(memory_lucidity_purge)
    assert inspect.iscoroutinefunction(memory_search_rrf)


def test_mcp_server_name():
    from mcp_server import mcp

    assert mcp.name == "ariel-memory"


def test_mcp_server_instructions():
    from mcp_server import mcp

    assert "Two-Layer" in mcp.instructions
    assert "user" in mcp.instructions
    assert "agent" in mcp.instructions


@pytest.mark.asyncio
async def test_mcp_lifespan():
    from mcp_server import lifespan, mcp

    async with lifespan(mcp) as ctx:
        assert ctx is not None
        assert hasattr(ctx, "mm")
        assert hasattr(ctx, "user_wiki")
        assert hasattr(ctx, "agent_wiki")


# ═══════════════════════════════════════════════════════════════
# CONFIG TESTS
# ═══════════════════════════════════════════════════════════════


def test_config_singleton():
    from config import Config

    c1 = Config()
    c2 = Config()
    assert c1 is c2


def test_config_get():
    from config import Config

    config = Config()
    # Default values should work
    assert config.get("layers", "user", "enabled", default=True) is True


def test_config_hooks():
    from config import Config

    config = Config()
    # Should not crash
    result = config.is_hook_enabled("user", "message_received")
    assert isinstance(result, bool)
