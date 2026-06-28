"""
MCP Server — Real MCP SDK implementation
FastMCP with 20 async tools, stdio + HTTP transports
"""

import asyncio
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

from mcp.server.fastmcp import Context, FastMCP

from shared.metrics import metrics

_data_dir = os.environ.get("MCP_MEMORY_DATA_DIR", str(Path.home() / ".mcp-ariel-memory"))
os.environ.setdefault("MCP_MEMORY_DATA_DIR", _data_dir)

sys.path.insert(0, str(Path(__file__).parent))

from config import config
from core import MemoryManager
from features.audit_trail import AuditTrail
from features.auth import api_key_auth, bearer_auth
from features.backup import BackupManager
from features.backup_cron import backup_cron
from features.import_export import ImportExport
from features.rate_limiting import RateLimiter
from graph.epistemic import EpistemicGraph
from graph.temporal import TemporalGraph
from hooks.agent_hooks import AgentHooks
from hooks.user_hooks import UserHooks
from lifecycle.consolidation import ConsolidationEngine
from lifecycle.emotion_trigger import EmotionTrigger
from lifecycle.forgetting import ForgettingSystem
from rag.engine import RAGEngine
from shared.cache import MemoryCache
from shared.read_only import read_only_replica
from wiki.file_wiki import FileWiki


class AppContext:
    def __init__(self):
        self.cache = MemoryCache()
        self.mm = MemoryManager(cache=self.cache)
        self.user_wiki = FileWiki(layer="user")
        self.agent_wiki = FileWiki(layer="agent")
        self.user_rag = RAGEngine(layer="user")
        self.agent_rag = RAGEngine(layer="agent")
        self.user_graph = EpistemicGraph(layer="user")
        self.agent_graph = EpistemicGraph(layer="agent")
        self.temporal = TemporalGraph()
        self.forgetting = ForgettingSystem()
        self.emotion_trigger = EmotionTrigger()
        self.consolidation = ConsolidationEngine()
        self.audit = AuditTrail()
        self.rate_limiter = RateLimiter()
        self.backup = BackupManager()
        self.import_export = ImportExport()
        self.user_hooks = UserHooks()
        self.agent_hooks = AgentHooks()


@asynccontextmanager
async def lifespan(server: FastMCP):
    # 1. Run migrations
    from shared.migrations import migration_manager

    result = await migration_manager.migrate()
    import logging

    logging.getLogger(__name__).info("Migrations: %s" % result)

    # 2. Sync read-only replica
    await asyncio.to_thread(read_only_replica.sync)

    # 3. Initialize context
    ctx = AppContext()
    backup_cron.start()
    try:
        yield ctx
    finally:
        backup_cron.stop()


mcp = FastMCP(
    "ariel-memory",
    instructions="Universal Two-Layer Memory MCP Server. Layer 1 (user) stores facts about users. Layer 2 (agent) stores agent identity, decisions, errors, and personality.",
    lifespan=lifespan,
)


def _get_ctx(ctx: Context) -> AppContext:
    return ctx.request_context.lifespan_context


# =============================================================================
# USER LAYER — 10 tools
# =============================================================================


@mcp.tool()
async def memory_user_remember(
    user_id: str = "default",
    key: str = "",
    value: str = "",
    importance: float = 0.5,
    ctx: Context = None,
) -> dict:
    """Save a fact about the user to long-term memory (L4 CoreMemory).

    Args:
        user_id: User identifier
        key: Fact key (e.g. "name", "language", "hobby")
        value: Fact value
        importance: Importance score 0.0-1.0 (default 0.5)
    """
    app = _get_ctx(ctx)
    metrics.inc("tool_calls")
    metrics.inc("tool_user_remember")

    # Hook: importance_gate — noise filter
    gate = app.user_hooks._importance_gate({"text": value})
    if gate.get("bypass"):
        return {"status": "skipped", "reason": "below_importance_threshold"}

    entry_id = await app.mm.user_memory(user_id).remember(key, value, importance)

    # Hook: emotion_trigger — emotional analysis
    should_save, emotion_reason, emotion_weight = app.emotion_trigger.should_save(value)
    if should_save:
        await app.mm.user_memory(user_id).l3.save(
            user_id, "%s=%s" % (key, value[:50]), emotion_weight, [emotion_reason]
        )

    return {"status": "ok", "entry_id": entry_id}


@mcp.tool()
async def memory_user_recall(
    user_id: str = "default",
    query: str = "",
    limit: int = 10,
    ctx: Context = None,
) -> dict:
    """Search user memory across L3 (episodes) and L4 (facts).

    Args:
        user_id: User identifier
        query: Search query
        limit: Max results (default 10)
    """
    app = _get_ctx(ctx)
    metrics.inc("tool_calls")
    metrics.inc("tool_user_recall")
    results = await app.mm.user_memory(user_id).recall(query, limit)
    return {"results": results, "count": len(results)}


@mcp.tool()
async def memory_user_forget(
    user_id: str = "default",
    key: str = "",
    ctx: Context = None,
) -> dict:
    """Delete a fact from user L4 memory.

    Args:
        user_id: User identifier
        key: Fact key to delete
    """
    app = _get_ctx(ctx)
    metrics.inc("tool_calls")
    metrics.inc("tool_user_forget")
    deleted = await app.mm.user_memory(user_id).forget(key)
    return {"deleted": deleted}


@mcp.tool()
async def memory_user_session_start(
    user_id: str = "default",
    ctx: Context = None,
) -> dict:
    """Start a new user memory session.

    Args:
        user_id: User identifier
    """
    app = _get_ctx(ctx)
    metrics.inc("tool_calls")
    metrics.inc("tool_user_session_start")
    session_id = await app.mm.user_memory(user_id).l2.create_session(user_id)
    return {"session_id": session_id}


@mcp.tool()
async def memory_user_session_end(
    user_id: str = "default",
    session_id: str = "",
    summary: str = "",
    ctx: Context = None,
) -> dict:
    """End a user session and save summary.

    Args:
        user_id: User identifier
        session_id: Session ID from session_start
        summary: Session summary
    """
    app = _get_ctx(ctx)
    metrics.inc("tool_calls")
    metrics.inc("tool_user_session_end")
    await app.mm.user_memory(user_id).l2.close_session(session_id, summary)
    return {"status": "ok"}


@mcp.tool()
async def memory_user_episode_save(
    user_id: str = "default",
    summary: str = "",
    weight: float = 0.5,
    tags: list[str] | None = None,
    ctx: Context = None,
) -> dict:
    """Save an important episode to L3 episodic memory.

    Args:
        user_id: User identifier
        summary: Episode description
        weight: Emotional weight 0.0-1.0 (default 0.5)
        tags: List of tags (e.g. ["greeting", "work"])
    """
    app = _get_ctx(ctx)
    metrics.inc("tool_calls")
    metrics.inc("tool_user_episode_save")
    episode_id = await app.mm.user_memory(user_id).l3.save(user_id, summary, weight, tags)
    return {"episode_id": episode_id}


@mcp.tool()
async def memory_user_episode_recall(
    user_id: str = "default",
    tag: str = "",
    limit: int = 10,
    ctx: Context = None,
) -> dict:
    """Recall episodes, optionally filtered by tag.

    Args:
        user_id: User identifier
        tag: Filter by tag (empty = all)
        limit: Max results (default 10)
    """
    app = _get_ctx(ctx)
    metrics.inc("tool_calls")
    metrics.inc("tool_user_episode_recall")
    if tag:
        episodes = await app.mm.user_memory(user_id).l3.search_by_tag(user_id, tag, limit)
    else:
        episodes = await app.mm.user_memory(user_id).l3.get_episodes(user_id, limit)
    return {"episodes": [{"id": e.episode_id, "summary": e.summary, "weight": e.emotional_weight} for e in episodes]}


@mcp.tool()
async def memory_user_graph_add(
    user_id: str = "default",
    content: str = "",
    node_type: str = "fact",
    tags: list[str] | None = None,
    ctx: Context = None,
) -> dict:
    """Add a node to the user epistemic graph.

    Args:
        user_id: User identifier
        content: Node content
        node_type: Node type (fact, decision, emotion, etc.)
        tags: Tags (e.g. ["fact_about_user", "user_preference"])
    """
    app = _get_ctx(ctx)
    metrics.inc("tool_calls")
    metrics.inc("tool_user_graph_add")
    node_id = await app.user_graph.add_node(user_id, content, node_type, tags)
    return {"node_id": node_id}


@mcp.tool()
async def memory_user_graph_query(
    user_id: str = "default",
    tag: str = "",
    node_type: str = "",
    limit: int = 20,
    ctx: Context = None,
) -> dict:
    """Query the user epistemic graph by tag or node type.

    Args:
        user_id: User identifier
        tag: Filter by tag
        node_type: Filter by node type
        limit: Max results (default 20)
    """
    app = _get_ctx(ctx)
    metrics.inc("tool_calls")
    metrics.inc("tool_user_graph_query")
    if tag:
        nodes = await app.user_graph.query_by_tag(user_id, tag, limit)
    elif node_type:
        nodes = await app.user_graph.query_by_type(user_id, node_type, limit)
    else:
        nodes = []
    return {"nodes": [{"id": n.node_id, "content": n.content, "type": n.node_type, "tags": n.tags} for n in nodes]}


@mcp.tool()
async def memory_user_stats(
    user_id: str = "default",
    ctx: Context = None,
) -> dict:
    """Get user memory statistics across all layers.

    Args:
        user_id: User identifier
    """
    app = _get_ctx(ctx)
    metrics.inc("tool_calls")
    metrics.inc("tool_user_stats")
    mem = app.mm.user_memory(user_id)
    l3_count = await mem.l3.get_episodes(user_id, 1000)
    return {
        "l1_buffer": mem.l1.size(),
        "l2_sessions": await mem.l2.count_sessions(user_id),
        "l3_episodes": len(l3_count),
        "l4_facts": await mem.l4.count(user_id),
        "wiki_pages": await app.user_wiki.count(),
        "graph_nodes": await app.user_graph.count_nodes(user_id),
    }


# =============================================================================
# AGENT LAYER — 10 tools
# =============================================================================


@mcp.tool()
async def memory_agent_remember(
    user_id: str = "default",
    key: str = "",
    value: str = "",
    importance: float = 0.5,
    ctx: Context = None,
) -> dict:
    """Save a decision, error pattern, or principle to agent identity memory.

    Args:
        user_id: User/agent identifier
        key: Fact key (e.g. "db_choice", "error_pattern", "principle")
        value: Fact value
        importance: Importance score 0.0-1.0 (default 0.5)
    """
    app = _get_ctx(ctx)
    metrics.inc("tool_calls")
    metrics.inc("tool_agent_remember")

    # Hook: error_occurred / decision_made — log to graph
    if "error" in key.lower():
        node_id = await app.agent_graph.add_node(user_id, value, "error_analysis", ["error_pattern"], importance)
    elif "decision" in key.lower():
        node_id = await app.agent_graph.add_node(user_id, value, "decision_log", ["decided_because"], importance)
    else:
        node_id = await app.agent_graph.add_node(user_id, value, "agent_fact", [], importance)

    entry_id = await app.mm.agent_memory(user_id).remember(key, value, importance)
    return {"status": "ok", "entry_id": entry_id, "graph_node_id": node_id}


@mcp.tool()
async def memory_agent_recall(
    user_id: str = "default",
    query: str = "",
    limit: int = 10,
    ctx: Context = None,
) -> dict:
    """Search agent identity memory.

    Args:
        user_id: User/agent identifier
        query: Search query
        limit: Max results (default 10)
    """
    app = _get_ctx(ctx)
    metrics.inc("tool_calls")
    metrics.inc("tool_agent_recall")
    results = await app.mm.agent_memory(user_id).recall(query, limit)
    return {"results": results, "count": len(results)}


@mcp.tool()
async def memory_agent_forget(
    user_id: str = "default",
    key: str = "",
    ctx: Context = None,
) -> dict:
    """Delete a fact from agent memory.

    Args:
        user_id: User/agent identifier
        key: Fact key to delete
    """
    app = _get_ctx(ctx)
    metrics.inc("tool_calls")
    metrics.inc("tool_agent_forget")
    deleted = await app.mm.agent_memory(user_id).forget(key)
    return {"deleted": deleted}


@mcp.tool()
async def memory_agent_session_start(
    user_id: str = "default",
    ctx: Context = None,
) -> dict:
    """Start a new agent session.

    Args:
        user_id: User/agent identifier
    """
    app = _get_ctx(ctx)
    metrics.inc("tool_calls")
    metrics.inc("tool_agent_session_start")
    session_id = await app.mm.agent_memory(user_id).l2.create_session(user_id)
    return {"session_id": session_id}


@mcp.tool()
async def memory_agent_session_end(
    user_id: str = "default",
    session_id: str = "",
    summary: str = "",
    ctx: Context = None,
) -> dict:
    """End an agent session and save summary.

    Args:
        user_id: User/agent identifier
        session_id: Session ID
        summary: Session summary
    """
    app = _get_ctx(ctx)
    metrics.inc("tool_calls")
    metrics.inc("tool_agent_session_end")
    await app.mm.agent_memory(user_id).l2.close_session(session_id, summary)
    return {"status": "ok"}


@mcp.tool()
async def memory_agent_episode_save(
    user_id: str = "default",
    summary: str = "",
    weight: float = 0.5,
    tags: list[str] | None = None,
    ctx: Context = None,
) -> dict:
    """Save an agent episode (decision, error, learning).

    Args:
        user_id: User/agent identifier
        summary: Episode description
        weight: Importance weight 0.0-1.0
        tags: Tags (e.g. ["decision", "error", "learning"])
    """
    app = _get_ctx(ctx)
    metrics.inc("tool_calls")
    metrics.inc("tool_agent_episode_save")
    episode_id = await app.mm.agent_memory(user_id).l3.save(user_id, summary, weight, tags)
    return {"episode_id": episode_id}


@mcp.tool()
async def memory_agent_episode_recall(
    user_id: str = "default",
    tag: str = "",
    limit: int = 10,
    ctx: Context = None,
) -> dict:
    """Recall agent episodes.

    Args:
        user_id: User/agent identifier
        tag: Filter by tag
        limit: Max results
    """
    app = _get_ctx(ctx)
    metrics.inc("tool_calls")
    metrics.inc("tool_agent_episode_recall")
    if tag:
        episodes = await app.mm.agent_memory(user_id).l3.search_by_tag(user_id, tag, limit)
    else:
        episodes = await app.mm.agent_memory(user_id).l3.get_episodes(user_id, limit)
    return {"episodes": [{"id": e.episode_id, "summary": e.summary, "weight": e.emotional_weight} for e in episodes]}


@mcp.tool()
async def memory_agent_graph_add(
    user_id: str = "default",
    content: str = "",
    node_type: str = "decision_log",
    tags: list[str] | None = None,
    ctx: Context = None,
) -> dict:
    """Add a node to the agent epistemic graph.

    Args:
        user_id: User/agent identifier
        content: Node content
        node_type: Type (decision_log, error_analysis, personality_evolution, etc.)
        tags: Tags (e.g. ["decided_because", "error_pattern"])
    """
    app = _get_ctx(ctx)
    metrics.inc("tool_calls")
    metrics.inc("tool_agent_graph_add")
    node_id = await app.agent_graph.add_node(user_id, content, node_type, tags)
    return {"node_id": node_id}


@mcp.tool()
async def memory_agent_graph_query(
    user_id: str = "default",
    tag: str = "",
    node_type: str = "",
    limit: int = 20,
    ctx: Context = None,
) -> dict:
    """Query the agent epistemic graph.

    Args:
        user_id: User/agent identifier
        tag: Filter by tag
        node_type: Filter by type
        limit: Max results
    """
    app = _get_ctx(ctx)
    metrics.inc("tool_calls")
    metrics.inc("tool_agent_graph_query")
    if tag:
        nodes = await app.agent_graph.query_by_tag(user_id, tag, limit)
    elif node_type:
        nodes = await app.agent_graph.query_by_type(user_id, node_type, limit)
    else:
        nodes = []
    return {"nodes": [{"id": n.node_id, "content": n.content, "type": n.node_type, "tags": n.tags} for n in nodes]}


@mcp.tool()
async def memory_agent_stats(
    user_id: str = "default",
    ctx: Context = None,
) -> dict:
    """Get agent memory statistics.

    Args:
        user_id: User/agent identifier
    """
    app = _get_ctx(ctx)
    metrics.inc("tool_calls")
    metrics.inc("tool_agent_stats")
    mem = app.mm.agent_memory(user_id)
    l3_count = await mem.l3.get_episodes(user_id, 1000)
    return {
        "l1_buffer": mem.l1.size(),
        "l2_sessions": await mem.l2.count_sessions(user_id),
        "l3_episodes": len(l3_count),
        "l4_facts": await mem.l4.count(user_id),
        "wiki_pages": await app.agent_wiki.count(),
        "graph_nodes": await app.agent_graph.count_nodes(user_id),
    }


# =============================================================================
# AUTH + BACKUP TOOLS
# =============================================================================


@mcp.tool()
async def memory_create_api_key(
    user_id: str = "default",
    label: str = "",
    ctx: Context = None,
) -> dict:
    """Create an API key for a user.

    Args:
        user_id: User to create key for
        label: Optional label for the key
    """
    metrics.inc("tool_calls")
    metrics.inc("tool_create_api_key")
    key = api_key_auth.create_key(user_id, label)
    return {"api_key": key, "user_id": user_id, "label": label}


@mcp.tool()
async def memory_revoke_api_key(
    api_key: str = "",
    ctx: Context = None,
) -> dict:
    """Revoke an API key.

    Args:
        api_key: The API key to revoke
    """
    metrics.inc("tool_calls")
    metrics.inc("tool_revoke_api_key")
    revoked = api_key_auth.revoke(api_key)
    return {"revoked": revoked}


@mcp.tool()
async def memory_list_api_keys(
    ctx: Context = None,
) -> dict:
    """List all API keys (redacted)."""
    metrics.inc("tool_calls")
    metrics.inc("tool_list_api_keys")
    return {"keys": api_key_auth.list_keys()}


@mcp.tool()
async def memory_backup_now(
    ctx: Context = None,
) -> dict:
    """Create an immediate backup of all databases."""
    metrics.inc("tool_calls")
    metrics.inc("tool_backup_now")
    path = await backup_cron.backup_now()
    return {"path": path}


@mcp.tool()
async def memory_backup_list(
    ctx: Context = None,
) -> dict:
    """List available backups."""
    metrics.inc("tool_calls")
    metrics.inc("tool_backup_list")
    backups = await backup_cron.list_backups()
    return {"backups": backups}


@mcp.tool()
async def memory_backup_restore(
    backup_name: str = "",
    ctx: Context = None,
) -> dict:
    """Restore from a backup.

    Args:
        backup_name: Name of the backup to restore
    """
    metrics.inc("tool_calls")
    metrics.inc("tool_backup_restore")
    result = await backup_cron.restore(backup_name)
    return result


@mcp.tool()
async def memory_backup_status(
    ctx: Context = None,
) -> dict:
    """Get backup cron status."""
    metrics.inc("tool_calls")
    metrics.inc("tool_backup_status")
    return backup_cron.status()


# =============================================================================
# SAGA + MIDDLEWARE + RRF TOOLS
# =============================================================================


@mcp.tool()
async def memory_saga_consolidate(
    user_id: str = "default",
    ctx: Context = None,
) -> dict:
    """Run consolidation saga: gather → distill → promote. Auto-rollback on failure.

    Args:
        user_id: User identifier
    """
    metrics.inc("tool_calls")
    metrics.inc("tool_saga_consolidate")
    app = _get_ctx(ctx)
    from shared.saga import create_consolidation_saga

    saga = create_consolidation_saga(user_id, mm=app.mm)
    result = await saga.execute({"user_id": user_id, "_mm": app.mm})
    return {"status": saga.status.value, "result": result, "steps": saga.get_state()["steps"]}


@mcp.tool()
async def memory_saga_backup(
    ctx: Context = None,
) -> dict:
    """Run backup saga: copy → verify. Auto-rollback on failure.

    Creates a verified backup of all databases.
    """
    metrics.inc("tool_calls")
    metrics.inc("tool_saga_backup")
    from shared.saga import create_backup_saga

    saga = create_backup_saga()
    result = await saga.execute()
    return {"status": saga.status.value, "result": result, "steps": saga.get_state()["steps"]}


@mcp.tool()
async def memory_sync_replica(
    ctx: Context = None,
) -> dict:
    """Sync read-only replica for dashboard/metrics (no load on main DB).

    Creates a read-only copy of memory.db for safe querying.
    """
    metrics.inc("tool_calls")
    metrics.inc("tool_sync_replica")
    result = await asyncio.to_thread(read_only_replica.sync)
    return {"synced": result, "ready": read_only_replica.is_ready()}


@mcp.tool()
async def memory_export(
    user_id: str = "default",
    ctx: Context = None,
) -> dict:
    """Export user memory to JSON file.

    Args:
        user_id: User to export
    """
    metrics.inc("tool_calls")
    metrics.inc("tool_export")
    app = _get_ctx(ctx)
    path = await app.import_export.export_user(user_id)
    return {"path": path}


@mcp.tool()
async def memory_import(
    file_path: str = "",
    target_user_id: str = "default",
    ctx: Context = None,
) -> dict:
    """Import memory from JSON file.

    Args:
        file_path: Path to export file
        target_user_id: Import as this user
    """
    metrics.inc("tool_calls")
    metrics.inc("tool_import")
    app = _get_ctx(ctx)
    result = await app.import_export.import_user(file_path, target_user_id)
    return result


@mcp.tool()
async def memory_list_exports(
    ctx: Context = None,
) -> dict:
    """List available export files."""
    metrics.inc("tool_calls")
    metrics.inc("tool_list_exports")
    app = _get_ctx(ctx)
    exports = app.import_export.list_exports()
    return {"exports": exports}


@mcp.tool()
async def memory_cleanup(
    user_id: str = "default",
    retention_days: int = 30,
    ctx: Context = None,
) -> dict:
    """Full memory cleanup: deduplicate facts, archive old audit logs, clean staging.

    Args:
        user_id: User identifier
        retention_days: Days to keep audit logs (default 30)
    """
    metrics.inc("tool_calls")
    metrics.inc("tool_cleanup")
    app = _get_ctx(ctx)
    results = {}

    # 1. Deduplicate core memory
    from features.compression import MemoryCompressor

    mc = MemoryCompressor()
    results["dedup_core"] = await mc.deduplicate_core(user_id)

    # 2. Compress old episodes
    results["compress_episodes"] = await mc.compress_episodes(user_id, 0.3)

    # 3. Clean DreamBuffer
    from shared.dream_buffer import dream_buffer

    results["dream_buffer_cleanup"] = await dream_buffer.cleanup_old(24, 500)

    # 4. Archive old audit logs
    from features.audit_trail import AuditTrail

    at = AuditTrail()
    archive_dir = str(Path.home() / ".mcp-ariel-memory" / "archives")
    results["audit_archive"] = await at.archive_and_prune(retention_days, archive_dir)

    # 5. Cleanup old backups
    from features.backup_cron import backup_cron

    results["backup_cleanup"] = await backup_cron.cleanup_old()

    # 6. Cleanup completed sagas
    from shared.saga import saga_watchdog

    results["saga_cleanup"] = await saga_watchdog.cleanup_completed()

    return results


@mcp.tool()
async def memory_lucidity_purge(
    user_id: str = "default",
    hours: int = 24,
    ctx: Context = None,
) -> dict:
    """Emergency purge: delete all data from the last N hours (data leak scenario).

    Args:
        user_id: User identifier
        hours: How many hours back to purge (default 24)
    """
    metrics.inc("tool_calls")
    metrics.inc("tool_lucidity_purge")
    results = {}
    cutoff = time.time() - (hours * 3600)

    # 1. Core memory — delete records from last N hours
    app = _get_ctx(ctx)
    conn = await app.mm.user_memory(user_id).l4._get_conn()
    try:
        cursor = conn.execute("DELETE FROM core_memory WHERE user_id=? AND created_at > ?", (user_id, cutoff))
        results["core_memory"] = cursor.rowcount
        conn.commit()
    finally:
        conn.close()

    # 2. Episodes — delete from last N hours
    conn = await app.mm.user_memory(user_id).l3._get_conn()
    try:
        cursor = conn.execute("DELETE FROM episodes WHERE user_id=? AND created_at > ?", (user_id, cutoff))
        results["episodes"] = cursor.rowcount
        conn.commit()
    finally:
        conn.close()

    # 3. DreamBuffer — clear staging
    from shared.dream_buffer import DreamBuffer

    db = DreamBuffer()
    results["staging"] = db.clear_staging(user_id)

    # 4. Audit trail — delete from last N hours
    from features.audit_trail import AuditTrail

    at = AuditTrail()
    conn = at._get_conn()
    try:
        cursor = conn.execute("DELETE FROM audit_log WHERE user_id=? AND timestamp > ?", (user_id, cutoff))
        results["audit"] = cursor.rowcount
        conn.commit()
    finally:
        conn.close()

    # 5. Graph nodes from last N hours (epistemic)
    from graph.epistemic import EpistemicGraph

    eg = EpistemicGraph(layer="user")
    conn = eg._get_conn()
    try:
        cursor = conn.execute("DELETE FROM epi_nodes WHERE user_id=? AND created_at > ?", (user_id, cutoff))
        results["graph_nodes"] = cursor.rowcount
        conn.commit()
    finally:
        conn.close()

    return results


@mcp.tool()
async def memory_user_context_inject(
    user_id: str = "default",
    ctx: Context = None,
) -> dict:
    """Return compressed summary for prompt injection (L4 top-10 + L3 top-3).

    Args:
        user_id: User identifier
    """
    metrics.inc("tool_calls")
    metrics.inc("tool_context_inject")
    app = _get_ctx(ctx)

    # L4: top-10 facts by importance
    l4_facts = await app.mm.user_memory(user_id).l4.get_all(user_id, 10)
    facts_text = "; ".join(["%s=%s" % (f.key, f.value[:30]) for f in l4_facts])

    # L3: top-3 episodes
    l3_episodes = await app.mm.user_memory(user_id).l3.get_episodes(user_id, 3)
    episodes_text = "; ".join(["%s" % e.summary[:50] for e in l3_episodes])

    # L1: last 5 messages
    l1_recent = app.mm.user_memory(user_id).l1.get_recent(5)
    recent_text = "; ".join(["%s: %s" % (r.role, r.content[:50]) for r in l1_recent])

    # Wiki: last 3 entries
    wiki_entries = await app.user_wiki.list_all(3)
    wiki_text = "; ".join(["[%s] %s" % (w.wiki_type, w.title) for w in wiki_entries])

    # Collect into single string
    context_parts = []
    if facts_text:
        context_parts.append("FACTS: " + facts_text)
    if episodes_text:
        context_parts.append("EPISODES: " + episodes_text)
    if recent_text:
        context_parts.append("RECENT: " + recent_text)
    if wiki_text:
        context_parts.append("WIKI: " + wiki_text)

    full_context = "\n".join(context_parts)

    return {
        "context": full_context,
        "l4_facts_count": len(l4_facts),
        "l3_episodes_count": len(l3_episodes),
        "l1_recent_count": len(l1_recent),
        "wiki_count": len(wiki_entries),
    }


@mcp.tool()
async def memory_search_rrf(
    query: str = "",
    user_id: str = "default",
    limit: int = 10,
    ctx: Context = None,
) -> dict:
    """Hybrid search using Reciprocal Rank Fusion (FTS5 + vector similarity).

    Combines full-text search with embedding similarity for better results.

    Args:
        query: Search query
        user_id: User identifier
        limit: Max results (default 10)
    """
    metrics.inc("tool_calls")
    metrics.inc("tool_search_rrf")
    app = _get_ctx(ctx)
    results = await app.user_rag.search_rrf(query, user_id, limit)
    return {"results": results, "count": len(results), "method": "rrf"}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Ariel Memory MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport: stdio (Claude Desktop) or http (web clients)",
    )
    parser.add_argument("--host", default="0.0.0.0", help="HTTP host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port (default: 8000)")
    parser.add_argument("--dashboard", action="store_true", help="Enable dashboard + metrics endpoints")
    args = parser.parse_args()

    if args.transport == "http":
        if args.dashboard:
            _run_with_dashboard(args.host, args.port)
        else:
            mcp.settings.host = args.host
            mcp.settings.port = args.port
            mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


def _run_with_dashboard(host: str, port: int):
    import uvicorn
    from starlette.applications import Starlette
    from starlette.middleware.cors import CORSMiddleware
    from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse
    from starlette.routing import Mount, Route

    from features.dashboard import Dashboard
    from features.rate_limiting import ConnectionLimiter, RateLimiter
    from shared.metrics import metrics as m

    dashboard = Dashboard()
    api_rate_limiter = RateLimiter()
    ws_limiter = ConnectionLimiter()

    def check_auth(request) -> bool:
        """Check Bearer token. Returns True if authorized."""
        auth_enabled = config.get("auth", "bearer_token_enabled", default=True)
        if not auth_enabled:
            return True
        auth = request.headers.get("Authorization", "")
        if not auth:
            return False
        return bearer_auth.verify(auth)

    def get_user_from_token(request) -> str:
        """Extract user_id from Bearer token or IP."""
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
            info = bearer_auth.verify(auth)
            if info:
                return info.get("user_id", "api")
        return request.client.host if request.client else "unknown"

    def check_rate_limit(request) -> bool:
        """Check rate limit for API endpoints."""
        rate_enabled = config.get("features", "rate_limiting", default=True)
        if not rate_enabled:
            return True
        user = get_user_from_token(request)
        result = api_rate_limiter.check(user)
        return result.get("allowed", True)

    async def dashboard_page(request):
        if not check_auth(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        if not check_rate_limit(request):
            return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)
        return HTMLResponse(dashboard.render_html())

    async def api_stats(request):
        if not check_auth(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        if not check_rate_limit(request):
            return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)
        user_id = request.query_params.get("user_id", "default")
        return JSONResponse(dashboard.get_stats(user_id))

    async def api_user_facts(request):
        if not check_auth(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        if not check_rate_limit(request):
            return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)
        user_id = request.query_params.get("user_id", "default")
        return JSONResponse(dashboard.get_user_facts(user_id))

    async def api_agent_facts(request):
        if not check_auth(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        if not check_rate_limit(request):
            return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)
        user_id = request.query_params.get("user_id", "default")
        return JSONResponse(dashboard.get_agent_facts(user_id))

    async def api_user_episodes(request):
        if not check_auth(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        if not check_rate_limit(request):
            return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)
        user_id = request.query_params.get("user_id", "default")
        return JSONResponse(dashboard.get_user_episodes(user_id))

    async def api_agent_episodes(request):
        if not check_auth(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        if not check_rate_limit(request):
            return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)
        user_id = request.query_params.get("user_id", "default")
        return JSONResponse(dashboard.get_agent_episodes(user_id))

    async def api_audit(request):
        if not check_auth(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        if not check_rate_limit(request):
            return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)
        return JSONResponse(dashboard.get_audit())

    async def metrics_endpoint(request):
        if not check_auth(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        if not check_rate_limit(request):
            return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)
        return PlainTextResponse(m.render_prometheus())

    async def metrics_json(request):
        if not check_auth(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        if not check_rate_limit(request):
            return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)
        return JSONResponse(m.render_json())

    async def auth_keys(request):
        if not check_auth(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        if not check_rate_limit(request):
            return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)
        from features.auth import api_key_auth

        return JSONResponse(api_key_auth.list_keys())

    async def auth_create(request):
        if not check_auth(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        if not check_rate_limit(request):
            return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)

    async def auth_create(request):
        if not check_auth(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        if not check_rate_limit(request):
            return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)
        from features.auth import api_key_auth

        body = await request.json()
        key = api_key_auth.create_key(body.get("user_id", "default"), body.get("label", ""))
        return JSONResponse({"api_key": key})

    async def backup_trigger(request):
        if not check_auth(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        if not check_rate_limit(request):
            return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)
        from features.backup_cron import backup_cron

        path = await backup_cron.backup_now()
        return JSONResponse({"path": path})

    async def backup_list(request):
        if not check_auth(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        if not check_rate_limit(request):
            return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)
        from features.backup_cron import backup_cron

        return JSONResponse(backup_cron.list_backups())

    app = Starlette(
        routes=[
            Route("/dashboard", dashboard_page),
            Route("/api/stats", api_stats),
            Route("/api/user/facts", api_user_facts),
            Route("/api/agent/facts", api_agent_facts),
            Route("/api/user/episodes", api_user_episodes),
            Route("/api/agent/episodes", api_agent_episodes),
            Route("/api/audit", api_audit),
            Route("/api/auth/keys", auth_keys),
            Route("/api/auth/create", auth_create, methods=["POST"]),
            Route("/api/backup/trigger", backup_trigger, methods=["POST"]),
            Route("/api/backup/list", backup_list),
            Route("/metrics", metrics_endpoint),
            Route("/metrics/json", metrics_json),
            Mount("/", app=mcp.streamable_http_app()),
        ],
    )

    from starlette.middleware.base import BaseHTTPMiddleware

    class AuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            auth = request.headers.get("Authorization", "")
            if auth and not bearer_auth.verify(auth):
                from starlette.responses import JSONResponse

                return JSONResponse({"error": "Invalid token"}, status_code=401)
            return await call_next(request)

    class WSConnectionMiddleware(BaseHTTPMiddleware):
        """Limit concurrent WebSocket/SSE connections."""

        async def dispatch(self, request, call_next):
            # Only check for /mcp endpoint (SSE/WebSocket)
            if request.url.path == "/mcp" and request.headers.get("upgrade", "").lower() == "websocket":
                user = request.headers.get("X-User-ID", request.client.host if request.client else "unknown")
                conn_id = "%s_%s" % (user, int(time.time() * 1000))
                acquired = ws_limiter.acquire(user, conn_id)
                if not acquired["allowed"]:
                    from starlette.responses import JSONResponse

                    return JSONResponse(
                        {
                            "error": "WebSocket connection limit exceeded",
                            "reason": acquired["reason"],
                            "current": acquired["current"],
                            "max": acquired["max"],
                        },
                        status_code=429,
                    )
            return await call_next(request)

    app.add_middleware(AuthMiddleware)
    app.add_middleware(WSConnectionMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "DELETE"],
        expose_headers=["Mcp-Session-Id"],
    )

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
