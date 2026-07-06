"""
Tests for auth — unique tests only.
"""

import pytest


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


@pytest.mark.asyncio
async def test_mcp_lifespan():
    from mcp_server.server import lifespan, mcp

    async with lifespan(mcp) as ctx:
        assert ctx is not None
        assert hasattr(ctx, "mm")
        assert hasattr(ctx, "user_wiki")
        assert hasattr(ctx, "agent_wiki")
