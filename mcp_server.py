"""
MCP Server — Real MCP SDK implementation
FastMCP with 20 async tools, stdio + HTTP transports
"""
import os
import sys
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP, Context

from shared.metrics import metrics

_data_dir = os.environ.get("MCP_MEMORY_DATA_DIR", str(Path.home() / ".mcp-ariel-memory"))
os.environ.setdefault("MCP_MEMORY_DATA_DIR", _data_dir)

sys.path.insert(0, str(Path(__file__).parent))

from core import memory_manager
from rag.engine import RAGEngine
from rag.router import RetrievalRouter
from rag.conflict import ConflictResolver
from graph.epistemic import EpistemicGraph
from graph.temporal import TemporalGraph
from lifecycle.forgetting import ForgettingSystem
from lifecycle.emotion_trigger import EmotionTrigger
from lifecycle.consolidation import ConsolidationEngine
from wiki.file_wiki import FileWiki
from features.audit_trail import AuditTrail
from features.rate_limiting import RateLimiter
from features.backup import BackupManager
from features.import_export import ImportExport
from features.auth import api_key_auth, bearer_auth
from features.backup_cron import backup_cron
from shared.cache import MemoryCache
from config import config


class AppContext:
    def __init__(self):
        self.mm = memory_manager
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
        self.cache = MemoryCache()


@asynccontextmanager
async def lifespan(server: FastMCP):
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
    entry_id = await asyncio.to_thread(
        app.mm.user_memory(user_id).remember, key, value, importance
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
    results = await asyncio.to_thread(
        app.mm.user_memory(user_id).recall, query, limit
    )
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
    deleted = await asyncio.to_thread(
        app.mm.user_memory(user_id).forget, key
    )
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
    session_id = await asyncio.to_thread(
        app.mm.user_memory(user_id).l2.create_session, user_id
    )
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
    await asyncio.to_thread(
        app.mm.user_memory(user_id).l2.close_session, session_id, summary
    )
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
    episode_id = await asyncio.to_thread(
        app.mm.user_memory(user_id).l3.save, user_id, summary, weight, tags
    )
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
        episodes = await asyncio.to_thread(
            app.mm.user_memory(user_id).l3.search_by_tag, user_id, tag, limit
        )
    else:
        episodes = await asyncio.to_thread(
            app.mm.user_memory(user_id).l3.get_episodes, user_id, limit
        )
    return {
        "episodes": [
            {"id": e.episode_id, "summary": e.summary, "weight": e.emotional_weight}
            for e in episodes
        ]
    }


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
    node_id = await asyncio.to_thread(
        app.user_graph.add_node, user_id, content, node_type, tags
    )
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
        nodes = await asyncio.to_thread(app.user_graph.query_by_tag, user_id, tag, limit)
    elif node_type:
        nodes = await asyncio.to_thread(app.user_graph.query_by_type, user_id, node_type, limit)
    else:
        nodes = []
    return {
        "nodes": [
            {"id": n.node_id, "content": n.content, "type": n.node_type, "tags": n.tags}
            for n in nodes
        ]
    }


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
    l3_count = await asyncio.to_thread(mem.l3.get_episodes, user_id, 1000)
    return {
        "l1_buffer": mem.l1.size(),
        "l2_sessions": await asyncio.to_thread(mem.l2.count_sessions, user_id),
        "l3_episodes": len(l3_count),
        "l4_facts": await asyncio.to_thread(mem.l4.count, user_id),
        "wiki_pages": await asyncio.to_thread(app.user_wiki.count),
        "graph_nodes": await asyncio.to_thread(app.user_graph.count_nodes, user_id),
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
    entry_id = await asyncio.to_thread(
        app.mm.agent_memory(user_id).remember, key, value, importance
    )
    return {"status": "ok", "entry_id": entry_id}


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
    results = await asyncio.to_thread(
        app.mm.agent_memory(user_id).recall, query, limit
    )
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
    deleted = await asyncio.to_thread(
        app.mm.agent_memory(user_id).forget, key
    )
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
    session_id = await asyncio.to_thread(
        app.mm.agent_memory(user_id).l2.create_session, user_id
    )
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
    await asyncio.to_thread(
        app.mm.agent_memory(user_id).l2.close_session, session_id, summary
    )
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
    episode_id = await asyncio.to_thread(
        app.mm.agent_memory(user_id).l3.save, user_id, summary, weight, tags
    )
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
        episodes = await asyncio.to_thread(
            app.mm.agent_memory(user_id).l3.search_by_tag, user_id, tag, limit
        )
    else:
        episodes = await asyncio.to_thread(
            app.mm.agent_memory(user_id).l3.get_episodes, user_id, limit
        )
    return {
        "episodes": [
            {"id": e.episode_id, "summary": e.summary, "weight": e.emotional_weight}
            for e in episodes
        ]
    }


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
    node_id = await asyncio.to_thread(
        app.agent_graph.add_node, user_id, content, node_type, tags
    )
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
        nodes = await asyncio.to_thread(app.agent_graph.query_by_tag, user_id, tag, limit)
    elif node_type:
        nodes = await asyncio.to_thread(app.agent_graph.query_by_type, user_id, node_type, limit)
    else:
        nodes = []
    return {
        "nodes": [
            {"id": n.node_id, "content": n.content, "type": n.node_type, "tags": n.tags}
            for n in nodes
        ]
    }


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
    l3_count = await asyncio.to_thread(mem.l3.get_episodes, user_id, 1000)
    return {
        "l1_buffer": mem.l1.size(),
        "l2_sessions": await asyncio.to_thread(mem.l2.count_sessions, user_id),
        "l3_episodes": len(l3_count),
        "l4_facts": await asyncio.to_thread(mem.l4.count, user_id),
        "wiki_pages": await asyncio.to_thread(app.agent_wiki.count),
        "graph_nodes": await asyncio.to_thread(app.agent_graph.count_nodes, user_id),
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
    path = await asyncio.to_thread(backup_cron.backup_now)
    return {"path": path}


@mcp.tool()
async def memory_backup_list(
    ctx: Context = None,
) -> dict:
    """List available backups."""
    metrics.inc("tool_calls")
    metrics.inc("tool_backup_list")
    backups = await asyncio.to_thread(backup_cron.list_backups)
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
    result = await asyncio.to_thread(backup_cron.restore, backup_name)
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
    from shared.saga import create_consolidation_saga
    saga = create_consolidation_saga(user_id)
    result = await saga.execute({"user_id": user_id})
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
    results["dedup_core"] = await asyncio.to_thread(mc.deduplicate_core, user_id)

    # 2. Compress old episodes
    results["compress_episodes"] = await asyncio.to_thread(mc.compress_episodes, user_id, 0.3)

    # 3. Clean DreamBuffer
    from shared.dream_buffer import dream_buffer
    results["dream_buffer_cleanup"] = await asyncio.to_thread(dream_buffer.cleanup_old, 24, 500)

    # 4. Archive old audit logs
    from features.audit_trail import AuditTrail
    at = AuditTrail()
    archive_dir = str(Path.home() / ".mcp-ariel-memory" / "archives")
    results["audit_archive"] = await asyncio.to_thread(at.archive_and_prune, retention_days, archive_dir)

    # 5. Cleanup old backups
    from features.backup_cron import backup_cron
    results["backup_cleanup"] = await asyncio.to_thread(backup_cron.cleanup_old)

    # 6. Cleanup completed sagas
    from shared.saga import saga_watchdog
    results["saga_cleanup"] = await asyncio.to_thread(saga_watchdog.cleanup_completed)

    return results


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
    results = await asyncio.to_thread(app.user_rag.search_rrf, query, user_id, limit)
    return {"results": results, "count": len(results), "method": "rrf"}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Ariel Memory MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio",
                        help="Transport: stdio (Claude Desktop) or http (web clients)")
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
    from starlette.routing import Mount, Route
    from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse
    from starlette.middleware.cors import CORSMiddleware

    from features.dashboard import Dashboard
    from features.auth import bearer_auth
    from shared.metrics import metrics as m

    dashboard = Dashboard()

    def check_auth(request) -> bool:
        """Проверка Bearer token. Возвращает True если авторизован."""
        auth_enabled = config.get("auth", "bearer_token_enabled", default=True)
        if not auth_enabled:
            return True
        auth = request.headers.get("Authorization", "")
        if not auth:
            return False
        return bearer_auth.verify(auth)

    async def dashboard_page(request):
        if not check_auth(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return HTMLResponse(dashboard.render_html())

    async def api_stats(request):
        if not check_auth(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        user_id = request.query_params.get("user_id", "default")
        return JSONResponse(dashboard.get_stats(user_id))

    async def api_user_facts(request):
        if not check_auth(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        user_id = request.query_params.get("user_id", "default")
        return JSONResponse(dashboard.get_user_facts(user_id))

    async def api_agent_facts(request):
        if not check_auth(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        user_id = request.query_params.get("user_id", "default")
        return JSONResponse(dashboard.get_agent_facts(user_id))

    async def api_user_episodes(request):
        if not check_auth(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        user_id = request.query_params.get("user_id", "default")
        return JSONResponse(dashboard.get_user_episodes(user_id))

    async def api_agent_episodes(request):
        if not check_auth(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        user_id = request.query_params.get("user_id", "default")
        return JSONResponse(dashboard.get_agent_episodes(user_id))

    async def api_audit(request):
        if not check_auth(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return JSONResponse(dashboard.get_audit())

    async def metrics_endpoint(request):
        if not check_auth(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return PlainTextResponse(m.render_prometheus())

    async def metrics_json(request):
        if not check_auth(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return JSONResponse(m.render_json())

    async def auth_keys(request):
        from features.auth import api_key_auth
        return JSONResponse(api_key_auth.list_keys())

    async def auth_create(request):
        from features.auth import api_key_auth
        body = await request.json()
        key = api_key_auth.create_key(body.get("user_id", "default"), body.get("label", ""))
        return JSONResponse({"api_key": key})

    async def backup_trigger(request):
        from features.backup_cron import backup_cron
        path = await asyncio.to_thread(backup_cron.backup_now)
        return JSONResponse({"path": path})

    async def backup_list(request):
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

    from starlette.middleware import Middleware
    from starlette.middleware.base import BaseHTTPMiddleware

    class AuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            auth = request.headers.get("Authorization", "")
            if auth and not bearer_auth.verify(auth):
                from starlette.responses import JSONResponse
                return JSONResponse({"error": "Invalid token"}, status_code=401)
            return await call_next(request)

    app.add_middleware(AuthMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "DELETE"],
        expose_headers=["Mcp-Session-Id"],
    )

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
