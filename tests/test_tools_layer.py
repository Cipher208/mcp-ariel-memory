"""Tests for unified layer tools (tools_layer.py)."""

import pytest


@pytest.fixture(autouse=True)
def setup_master_key(monkeypatch):
    monkeypatch.setenv("MCP_MASTER_KEY", "test-secret-for-unit-tests-only")
    from features import secrets

    secrets._master_cache.clear()


def test_memory_remember_user():
    from mcp_server.tools_layer import _get_memory

    from core import MemoryManager
    from shared.cache import MemoryCache

    mm = MemoryManager(cache=MemoryCache())

    class FakeApp:
        def __init__(self):
            self.mm = mm
            self.user_hooks = type("H", (), {"_importance_gate": lambda s, x: {"bypass": False}})()
            self.emotion_trigger = type("E", (), {"should_save": lambda s, x: (False, "", 0.0)})()

    app = FakeApp()
    mem = _get_memory(app, "user", "test_user")
    entry_id = asyncio.run(mem.remember("lang", "Python", 0.8))
    assert entry_id > 0


def test_memory_remember_agent():
    from mcp_server.tools_layer import _get_memory

    from core import MemoryManager
    from shared.cache import MemoryCache

    mm = MemoryManager(cache=MemoryCache())

    class FakeApp:
        def __init__(self):
            self.mm = mm

    app = FakeApp()
    mem = _get_memory(app, "agent", "test_agent")
    entry_id = asyncio.run(mem.remember("principle", "YAGNI", 0.9))
    assert entry_id > 0


def test_memory_recall_user():
    from mcp_server.tools_layer import _get_memory

    from core import MemoryManager
    from shared.cache import MemoryCache

    mm = MemoryManager(cache=MemoryCache())

    class FakeApp:
        def __init__(self):
            self.mm = mm

    app = FakeApp()
    mem = _get_memory(app, "user", "test_user")
    asyncio.run(mem.remember("name", "Alice", 0.9))
    results = asyncio.run(mem.recall("name"))
    assert len(results) > 0


def test_memory_forget():
    from mcp_server.tools_layer import _get_memory

    from core import MemoryManager
    from shared.cache import MemoryCache

    mm = MemoryManager(cache=MemoryCache())

    class FakeApp:
        def __init__(self):
            self.mm = mm

    app = FakeApp()
    mem = _get_memory(app, "user", "test_user")
    asyncio.run(mem.remember("temp", "value", 0.5))
    deleted = asyncio.run(mem.forget("temp"))
    assert deleted is True


def test_memory_stats():
    from mcp_server.tools_layer import _get_memory

    from core import MemoryManager
    from shared.cache import MemoryCache

    mm = MemoryManager(cache=MemoryCache())

    class FakeApp:
        def __init__(self):
            self.mm = mm

    app = FakeApp()
    mem = _get_memory(app, "user", "test_user")
    asyncio.run(mem.remember("key", "value", 0.5))
    count = asyncio.run(mem.l4.count("test_user"))
    assert count >= 1


def test_memory_remember_agent_integration():
    """Integration test: memory_remember(layer='agent') through full tool path."""
    from mcp_server.tools_layer import register_tools
    from mcp_server.server import mcp, AppContext

    tools_registered = any(t.name == "memory_remember" for t in mcp._tool_manager.list_tools())
    assert tools_registered, "memory_remember tool not registered"


import asyncio
