"""
Integration tests for all 37 MCP tools.
Tests the full tool pipeline: tool call → core modules → database → response.
"""

import asyncio
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# Ensure migrations run before any test
async def _setup():
    from shared.migrations import migration_manager

    await migration_manager.migrate()


asyncio.run(_setup())


@pytest.fixture
async def mm():
    """Get the global MemoryManager."""
    from core import memory_manager

    return memory_manager


# ═══════════════════════════════════════════════════════════════
# USER LAYER (10 tools)
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_user_remember(mm):
    user = mm.user_memory("test_integ")
    entry_id = await user.remember("name", "Alice", 0.9)
    assert entry_id > 0

    entry = await user.l4.get("test_integ", "name")
    assert entry is not None
    assert entry.value == "Alice"


@pytest.mark.asyncio
async def test_user_recall(mm):
    user = mm.user_memory("test_integ")
    await user.remember("lang", "Python", 0.8)
    results = await user.recall("Python")
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_user_forget(mm):
    user = mm.user_memory("test_integ")
    await user.remember("temp_key", "temp_value", 0.5)
    deleted = await user.forget("temp_key")
    assert deleted is True


@pytest.mark.asyncio
async def test_user_session(mm):
    user = mm.user_memory("test_integ")
    session_id = await user.l2.create_session("test_integ")
    assert session_id.startswith("sess_")


@pytest.mark.asyncio
async def test_user_episode(mm):
    user = mm.user_memory("test_integ")
    episode_id = await user.l3.save("test_integ", "Met team", 0.8, ["work"])
    assert episode_id > 0


@pytest.mark.asyncio
async def test_user_graph(mm):
    from graph.epistemic import EpistemicGraph
    from shared.connection import connection_manager

    eg = EpistemicGraph(layer="user", cm=connection_manager)
    await eg.init_db()

    node_id = await eg.add_node("test_integ", "Fact A", "fact", ["tag1"])
    assert node_id > 0

    nodes = await eg.query_by_tag("test_integ", "tag1")
    assert len(nodes) >= 1


@pytest.mark.asyncio
async def test_user_stats(mm):
    user = mm.user_memory("test_integ")
    await user.remember("stat_key", "stat_value", 0.9)
    context = await user.get_context()
    assert isinstance(context, str)


# ═══════════════════════════════════════════════════════════════
# AGENT LAYER (10 tools)
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_agent_remember(mm):
    agent = mm.agent_memory("test_integ")
    entry_id = await agent.remember("approach", "YAGNI", 0.9)
    assert entry_id > 0


@pytest.mark.asyncio
async def test_agent_recall(mm):
    agent = mm.agent_memory("test_integ")
    await agent.remember("principle", "Keep it simple", 0.8)
    results = await agent.recall("simple")
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_agent_forget(mm):
    agent = mm.agent_memory("test_integ")
    await agent.remember("temp", "value", 0.5)
    deleted = await agent.forget("temp")
    assert deleted is True


@pytest.mark.asyncio
async def test_agent_session(mm):
    agent = mm.agent_memory("test_integ")
    session_id = await agent.l2.create_session("test_integ")
    assert session_id.startswith("sess_")


@pytest.mark.asyncio
async def test_agent_episode(mm):
    agent = mm.agent_memory("test_integ")
    episode_id = await agent.l3.save("test_integ", "Learned pattern", 0.7, ["learning"])
    assert episode_id > 0


@pytest.mark.asyncio
async def test_agent_graph(mm):
    from graph.epistemic import EpistemicGraph
    from shared.connection import connection_manager

    eg = EpistemicGraph(layer="agent", cm=connection_manager)
    await eg.init_db()

    node_id = await eg.add_node("test_integ", "Use type hints", "principle", ["coding"])
    assert node_id > 0


@pytest.mark.asyncio
async def test_agent_stats(mm):
    agent = mm.agent_memory("test_integ")
    await agent.remember("rule", "Test first", 0.9)
    context = await agent.get_context()
    assert isinstance(context, str)


# ═══════════════════════════════════════════════════════════════
# RAG + SEARCH (5 tools)
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_rag_ingest_search():
    from rag.engine import RAGEngine
    from shared.connection import connection_manager

    rag = RAGEngine(cm=connection_manager)
    await rag.init_db()

    await rag.ingest_text("Python Tips", "Use type hints", user_id="test_integ")
    results = await rag.search("type hints", user_id="test_integ")
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_rag_rrf():
    from rag.engine import RAGEngine
    from shared.connection import connection_manager

    rag = RAGEngine(cm=connection_manager)
    await rag.init_db()

    await rag.ingest_text("Test Doc", "Hello world", user_id="test_integ")
    results = await rag.search_rrf("Hello", user_id="test_integ", limit=5)
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_rag_relations():
    from rag.engine import RAGEngine
    from shared.connection import connection_manager

    rag = RAGEngine(cm=connection_manager)
    await rag.init_db()

    page_id = await rag.ingest_text("Page A", "Content A", user_id="test_integ")
    page_id2 = await rag.ingest_text("Page B", "Content B", user_id="test_integ")
    await rag.add_relation(page_id, page_id2, "elaborates", 0.8)

    relations = await rag.get_relations(page_id)
    assert len(relations) >= 1


@pytest.mark.asyncio
async def test_conflict_resolver():
    from rag.conflict import ConflictResolver
    from shared.connection import connection_manager

    cr = ConflictResolver(cm=connection_manager)

    result = await cr.check("test_integ", "Python is great")
    assert result["is_conflict"] is False


@pytest.mark.asyncio
async def test_retrieval_router():
    from rag.router import RetrievalRouter

    router = RetrievalRouter(user_id="test_integ")
    result = await router.route("How to use Python?")
    assert hasattr(result, "strategy")
    assert hasattr(result, "context")


# ═══════════════════════════════════════════════════════════════
# GRAPH (4 tools)
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_epistemic_graph():
    from graph.epistemic import EpistemicGraph
    from shared.connection import connection_manager

    eg = EpistemicGraph(layer="user", cm=connection_manager)
    await eg.init_db()

    n1 = await eg.add_node("test_integ", "Fact A", "fact", ["tag1"])
    n2 = await eg.add_node("test_integ", "Fact B", "fact", ["tag1"])
    await eg.add_edge(n1, n2, "related", 0.8)

    neighbors = await eg.get_neighbors(n1)
    assert len(neighbors) >= 1


@pytest.mark.asyncio
async def test_epistemic_path():
    from graph.epistemic import EpistemicGraph
    from shared.connection import connection_manager

    eg = EpistemicGraph(layer="user", cm=connection_manager)
    await eg.init_db()

    n1 = await eg.add_node("test_path", "Node 1", "fact", [])
    n2 = await eg.add_node("test_path", "Node 2", "fact", [])
    n3 = await eg.add_node("test_path", "Node 3", "fact", [])
    await eg.add_edge(n1, n2, "links", 0.8)
    await eg.add_edge(n2, n3, "links", 0.8)

    path = await eg.find_path(n1, n3)
    assert len(path) >= 1


@pytest.mark.asyncio
async def test_temporal_graph():
    from graph.temporal import TemporalGraph
    from shared.connection import connection_manager

    tg = TemporalGraph(cm=connection_manager)
    await tg.init_db()

    e1 = await tg.add_event("test_integ", "message", "Hello")
    e2 = await tg.add_event("test_integ", "message", "World")
    await tg.link_events(e1, e2, "follows", 0.8)

    timeline = await tg.get_timeline("test_integ")
    assert len(timeline) >= 2


# ═══════════════════════════════════════════════════════════════
# LIFECYCLE (3 tools)
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_forgetting():
    from lifecycle.forgetting import ForgettingSystem

    fs = ForgettingSystem()
    result = await fs.cleanup()
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_emotion_trigger():
    from lifecycle.emotion_trigger import EmotionTrigger

    et = EmotionTrigger()
    should_save, reason, weight = et.should_save("I love this project!")
    assert isinstance(should_save, bool)
    assert isinstance(weight, float)


@pytest.mark.asyncio
async def test_consolidation():
    from lifecycle.consolidation import ConsolidationEngine

    ce = ConsolidationEngine()
    stats = await ce.get_stats("test_integ")
    assert isinstance(stats, dict)


# ═══════════════════════════════════════════════════════════════
# HOOKS (3 tools)
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_hook_registry():
    from hooks.registry import HookRegistry

    hr = HookRegistry()
    hr.register("custom_hook", lambda ctx: {"ok": True})
    result = hr.fire("custom_hook", "user", {})
    assert result["handler_count"] == 1


@pytest.mark.asyncio
async def test_user_hooks():
    from hooks.user_hooks import UserHooks

    uh = UserHooks()
    importance = uh._calculate_importance("I love Python programming!")
    assert 0.0 <= importance <= 1.0


@pytest.mark.asyncio
async def test_agent_hooks():
    from hooks.agent_hooks import AgentHooks
    from shared.migrations import migration_manager

    await migration_manager.migrate()
    ah = AgentHooks()
    result = ah._error_occurred({"error": "test error", "context": "testing"})
    assert isinstance(result, dict)


# ═══════════════════════════════════════════════════════════════
# WIKI (3 tools)
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_file_wiki():
    from shared.connection import connection_manager
    from wiki.file_wiki import FileWiki

    tmpdir = tempfile.mkdtemp()
    fw = FileWiki(layer="user", base_dir=tmpdir, cm=connection_manager)
    await fw.init_db()

    path = await fw.add("diary", "Day 1", "Started project", tags=["work"])
    assert path is not None

    results = await fw.search("project")
    assert len(results) >= 1

    import shutil

    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.mark.asyncio
async def test_user_wiki():
    from shared.connection import connection_manager
    from wiki.user_wiki import UserWiki

    uw = UserWiki(cm=connection_manager)
    await uw.init_db()

    entry_id = await uw.add("test_integ", "diary", "Day 1", "Content", ["work"])
    assert entry_id > 0


@pytest.mark.asyncio
async def test_agent_wiki():
    from shared.connection import connection_manager
    from wiki.agent_wiki import AgentWiki

    aw = AgentWiki(cm=connection_manager)
    await aw.init_db()

    entry_id = await aw.add("test_integ", "decision_log", "Choice A", "Chose A", [])
    assert entry_id > 0


# ═══════════════════════════════════════════════════════════════
# FEATURES (8 tools)
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_auth():
    from features.auth import APIKeyAuth

    auth = APIKeyAuth()
    key = auth.create_key("test_integ", "test key")
    assert key.startswith("ak_")

    info = auth.verify(key)
    assert info is not None
    assert info["user_id"] == "test_integ"


@pytest.mark.asyncio
async def test_bearer_auth():
    from features.auth import BearerAuth

    ba = BearerAuth()
    token = ba.get_token()
    assert token.startswith("mt_")
    assert ba.verify("Bearer " + token) is True


@pytest.mark.asyncio
async def test_backup():
    from features.backup import BackupManager

    bm = BackupManager()
    path = await bm.backup(label="test")
    assert path is not None


@pytest.mark.asyncio
async def test_audit_trail():
    from features.audit_trail import AuditTrail

    at = AuditTrail()
    await at._init_db()
    await at.log("test_integ", "test_action", "user", "target_123", {"key": "value"})
    history = await at.get_history("test_integ")
    assert len(history) >= 1


@pytest.mark.asyncio
async def test_rate_limiter():
    from features.rate_limiting import RateLimiter

    rl = RateLimiter()
    result = await rl.check("test_integ")
    assert "allowed" in result


@pytest.mark.asyncio
async def test_import_export():
    from features.import_export import ImportExport

    ie = ImportExport()
    exports = ie.list_exports()
    assert isinstance(exports, list)


@pytest.mark.asyncio
async def test_compression():
    from features.compression import MemoryCompressor

    mc = MemoryCompressor()
    stats = await mc.get_stats("test_integ")
    assert isinstance(stats, dict)


@pytest.mark.asyncio
async def test_dashboard():
    from features.dashboard import Dashboard

    d = Dashboard()
    stats = await d.get_stats("test_integ")
    assert isinstance(stats, dict)
    assert "l1_buffer" in stats
    assert "l4_facts" in stats


# ═══════════════════════════════════════════════════════════════
# SHARED (10 tools)
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_cache():
    from shared.cache import MemoryCache

    cache = MemoryCache()
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"
    assert cache.size() == 1
    cache.clear()
    assert cache.size() == 0


@pytest.mark.asyncio
async def test_saga():
    from shared.saga import Saga

    saga = Saga("test_saga")
    saga.add_step("step1", lambda d: {"ok": True})
    result = await saga.execute()
    assert result is not None


@pytest.mark.asyncio
async def test_middleware():
    from shared.middleware import MiddlewareContext, MiddlewarePipeline

    pipeline = MiddlewarePipeline()
    ctx = MiddlewareContext(user_id="test_integ")
    result = await pipeline.execute(ctx, lambda c: {"ok": True})
    assert result["ok"] is True


@pytest.mark.asyncio
async def test_embeddings():
    from shared.embeddings import EmbeddingCache

    cache = EmbeddingCache()
    emb = await cache.embed_single("Hello world")
    assert isinstance(emb, list)
    assert len(emb) > 0


@pytest.mark.asyncio
async def test_metrics():
    from shared.metrics import metrics

    metrics.inc("test_counter")
    metrics.gauge("test_gauge", 1.0)
    json_out = metrics.render_json()
    assert "counters" in json_out
    assert "test_counter" in json_out["counters"]


@pytest.mark.asyncio
async def test_dream_buffer():
    from shared.dream_buffer import DreamBuffer

    db = DreamBuffer()
    await db.add("test_integ", "sess1", "test content", importance=0.6)
    staging = await db.get_staging("test_integ")
    assert len(staging) >= 1
    await db.clear_staging("test_integ")


@pytest.mark.asyncio
async def test_archived_memories():
    from shared.archived_memories import ArchivedMemories

    am = ArchivedMemories()
    archive_id = await am.archive("test_integ", "Old memory", importance=0.2, reason="inactive")
    assert archive_id > 0


@pytest.mark.asyncio
async def test_migrations():
    from shared.migrations import MigrationManager

    mm = MigrationManager()
    version = await mm.get_current_version()
    assert isinstance(version, int)


@pytest.mark.asyncio
async def test_read_only():
    from shared.read_only import ReadOnlyReplica

    ror = ReadOnlyReplica()
    is_ready = ror.is_ready()
    assert isinstance(is_ready, bool)


@pytest.mark.asyncio
async def test_connection_manager():
    from shared.connection import AsyncConnectionManager

    cm = AsyncConnectionManager()
    conn = await cm.get("test_integ.db")
    assert conn is not None
    stats = cm.stats()
    assert stats["connections"] >= 1
    await cm.close_all()
