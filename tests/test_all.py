"""Basic tests for mcp-ariel-memory."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_mcp_tools_count():
    from mcp_server import mcp
    tools = mcp._tool_manager.list_tools()
    assert len(tools) >= 20  # 20 core + auth/backup tools


def test_mcp_tools_are_async():
    import inspect
    from mcp_server import (
        memory_user_remember, memory_user_recall, memory_user_forget,
        memory_user_session_start, memory_user_session_end,
        memory_user_episode_save, memory_user_episode_recall,
        memory_user_graph_add, memory_user_graph_query, memory_user_stats,
        memory_agent_remember, memory_agent_recall, memory_agent_forget,
        memory_agent_session_start, memory_agent_session_end,
        memory_agent_episode_save, memory_agent_episode_recall,
        memory_agent_graph_add, memory_agent_graph_query, memory_agent_stats,
    )
    funcs = [
        memory_user_remember, memory_user_recall, memory_user_forget,
        memory_user_session_start, memory_user_session_end,
        memory_user_episode_save, memory_user_episode_recall,
        memory_user_graph_add, memory_user_graph_query, memory_user_stats,
        memory_agent_remember, memory_agent_recall, memory_agent_forget,
        memory_agent_session_start, memory_agent_session_end,
        memory_agent_episode_save, memory_agent_episode_recall,
        memory_agent_graph_add, memory_agent_graph_query, memory_agent_stats,
    ]
    assert all(inspect.iscoroutinefunction(f) for f in funcs)


def test_backward_compat():
    from server import MemoryMCPServer
    s = MemoryMCPServer()
    r = s.call("memory.user.remember", user_id="test", key="k", value="v")
    assert r["status"] == "ok"


def test_user_remember_recall():
    from core import memory_manager
    mm = memory_manager
    mm.user_memory("test_user").remember("lang", "Python", 0.8)
    results = mm.user_memory("test_user").recall("lang")
    assert len(results) > 0
    assert results[0]["key"] == "lang"


def test_agent_remember_recall():
    from core import memory_manager
    mm = memory_manager
    mm.agent_memory("test_agent").remember("rule", "YAGNI", 0.9)
    results = mm.agent_memory("test_agent").recall("rule")
    assert len(results) > 0


def test_rag_engine():
    from rag.engine import RAGEngine
    rag = RAGEngine(layer="test")
    rag.ingest_text("Test Page", "Python is great for AI", user_id="test")
    results = rag.search("Python", user_id="test")
    assert len(results) > 0


def test_epistemic_graph():
    from graph.epistemic import EpistemicGraph
    g = EpistemicGraph(layer="test")
    n = g.add_node("test", "Likes Python", "fact", ["fact_about_user"])
    nodes = g.query_by_tag("test", "fact_about_user")
    assert len(nodes) >= 1


def test_user_wiki():
    from wiki.file_wiki import FileWiki
    w = FileWiki(layer="user")
    path = w.add("diary", "Day 1", "Started project")
    assert path is not None
    results = w.search("project")
    assert len(results) > 0


def test_audit_trail():
    from features.audit_trail import AuditTrail
    at = AuditTrail()
    at.log("test", "test_action")
    history = at.get_history("test")
    assert len(history) >= 1


def test_cache():
    from shared.cache import MemoryCache
    mc = MemoryCache(max_size=5, ttl=60)
    mc.set("key", "value")
    assert mc.get("key") == "value"
    mc.delete("key")
    assert mc.get("key") is None
