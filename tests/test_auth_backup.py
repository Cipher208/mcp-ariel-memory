"""
Tests for auth, MCP metadata, and config — unique tests only.
Backup/audit/rate_limiter/import_export are tested in test_integration.py.
"""

import pytest


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
# MCP AUTO-START TESTS
# ═══════════════════════════════════════════════════════════════


def test_mcp_tools_count():
    from mcp_server import mcp

    tools = mcp._tool_manager.list_tools()
    assert len(tools) >= 15


def test_mcp_tools_are_async():
    import inspect
    from mcp_server import mcp

    tools = mcp._tool_manager.list_tools()
    tool_names = [t.name for t in tools]
    assert "memory_remember" in tool_names
    assert "memory_backup" in tool_names
    assert "memory_api_key" in tool_names
    assert "memory_lucidity_purge" in tool_names
    assert "memory_search" in tool_names

    for tool in tools:
        assert inspect.iscoroutinefunction(tool.fn), f"{tool.name} is not async"


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
    from mcp_server.server import lifespan, mcp

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
    assert config.get("layers", "user", "enabled", default=True) is True


def test_config_hooks():
    from config import Config

    config = Config()
    result = config.is_hook_enabled("user", "message_received")
    assert isinstance(result, bool)
