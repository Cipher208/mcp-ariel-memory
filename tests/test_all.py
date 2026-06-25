"""Basic tests for mcp-ariel-memory (async)."""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Ensure migrations run before any test
async def _setup():
    from shared.migrations import migration_manager
    await migration_manager.migrate()
asyncio.run(_setup())


def test_mcp_tools_count():
    from mcp_server import mcp
    tools = mcp._tool_manager.list_tools()
    assert len(tools) >= 20


def test_mcp_tools_are_async():
    import inspect
    from mcp_server import memory_user_remember, memory_agent_remember
    assert inspect.iscoroutinefunction(memory_user_remember)
    assert inspect.iscoroutinefunction(memory_agent_remember)


def test_backward_compat():
    from server import MemoryMCPServer
    s = MemoryMCPServer()
    r = s.call("memory.user.remember", user_id="test", key="k", value="v")
    assert r.get("status") == "ok" or "entry_id" in r


def test_user_remember_recall():
    from core import memory_manager
    mm = memory_manager

    async def t():
        await mm.user_memory("test_user").remember("lang", "Python", 0.8)
        results = await mm.user_memory("test_user").recall("lang")
        assert len(results) > 0
        assert results[0]["key"] == "lang"

    asyncio.run(t())


def test_agent_remember_recall():
    from core import memory_manager
    mm = memory_manager

    async def t():
        await mm.agent_memory("test_agent").remember("rule", "YAGNI", 0.9)
        results = await mm.agent_memory("test_agent").recall("rule")
        assert len(results) > 0

    asyncio.run(t())


def test_rag_engine():
    from rag.engine import RAGEngine

    async def t():
        rag = RAGEngine(layer="test")
        await rag.ingest_text("Test Page", "Python is great for AI", user_id="test")
        results = await rag.search("Python", user_id="test")
        assert len(results) > 0

    asyncio.run(t())


def test_epistemic_graph():
    from graph.epistemic import EpistemicGraph

    async def t():
        g = EpistemicGraph(layer="test")
        n = await g.add_node("test", "Likes Python", "fact", ["fact_about_user"])
        nodes = await g.query_by_tag("test", "fact_about_user")
        assert len(nodes) >= 1

    asyncio.run(t())


def test_user_wiki():
    from wiki.file_wiki import FileWiki

    async def t():
        w = FileWiki(layer="user")
        path = await w.add("work_notes", "Day 1", "Started project")
        assert path is not None
        results = await w.search("project")
        assert len(results) > 0

    asyncio.run(t())


def test_audit_trail():
    from features.audit_trail import AuditTrail

    async def t():
        at = AuditTrail()
        await at.log("test", "test_action")
        history = await at.get_history("test")
        assert len(history) >= 1

    asyncio.run(t())


def test_cache():
    from shared.cache import MemoryCache
    mc = MemoryCache(max_size=5, ttl=60)
    mc.set("key", "value")
    assert mc.get("key") == "value"
    mc.delete("key")
    assert mc.get("key") is None
