"""End-to-end tests for MCP tool functions — full logic path.

Tests the complete pipeline: tool function → hooks → core modules → database → response.
Unlike test_tools_unit.py (which uses mocks), these test actual data flow.
"""

import asyncio
import pytest
from unittest.mock import MagicMock
from mcp_server.tools_layer import (
    memory_remember, memory_recall, memory_forget,
    memory_session_start, memory_session_end,
    memory_episode_save, memory_episode_recall,
    memory_graph_add, memory_graph_query,
    memory_stats, memory_context_inject,
)


# ── AppContext fixture using global singletons ──

def _make_app():
    """Create real AppContext using global singletons."""
    from core import memory_manager
    from shared.cache import MemoryCache
    from graph.epistemic import EpistemicGraph
    from wiki.manager import WikiManager
    from lifecycle.emotion_trigger import EmotionTrigger
    from features.rate_limiting import RateLimiter
    from hooks.user_hooks import UserHooks
    from hooks.agent_hooks import AgentHooks

    class App:
        pass

    app = App()
    app.mm = memory_manager
    app.cache = MemoryCache()
    app.user_wiki = WikiManager(layer="user")
    app.agent_wiki = WikiManager(layer="agent")
    app.user_graph = EpistemicGraph(layer="user")
    app.agent_graph = EpistemicGraph(layer="agent")
    app.emotion_trigger = EmotionTrigger()
    app.rate_limiter = RateLimiter()
    app.user_hooks = UserHooks()
    app.agent_hooks = AgentHooks()
    return app


def _make_ctx(app):
    """Create mock MCP ctx pointing to real AppContext."""
    ctx = MagicMock()
    ctx.request_context = MagicMock()
    ctx.request_context.lifespan_context = app
    return ctx


# ═══════════════════════════════════════════════════════════════
# memory_remember — full logic path
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_remember_user_full_flow():
    """remember → L4 storage → recall retrieves same data."""
    app = _make_app()
    ctx = _make_ctx(app)

    result = await memory_remember(
        layer="user", user_id="e2e_user", key="e2e_name",
        value="Alice", importance=0.9, ctx=ctx,
    )
    assert result["status"] == "ok"

    # Verify data is actually stored in L4
    mem = app.mm.user_memory("e2e_user")
    entry = await mem.l4.get("e2e_user", "e2e_name")
    assert entry is not None
    assert entry.value == "Alice"


@pytest.mark.asyncio
async def test_remember_agent_full_flow():
    """remember agent → L4 + graph node creation."""
    app = _make_app()
    ctx = _make_ctx(app)

    result = await memory_remember(
        layer="agent", user_id="e2e_agent", key="e2e_decision",
        value="Use async/await", importance=0.8, ctx=ctx,
    )
    assert result["status"] == "ok"
    assert "graph_node_id" in result

    # Verify L4 storage
    mem = app.mm.agent_memory("e2e_agent")
    entry = await mem.l4.get("e2e_agent", "e2e_decision")
    assert entry is not None
    assert entry.value == "Use async/await"


@pytest.mark.asyncio
async def test_remember_triggers_hooks():
    """remember should fire hooks (message_received, emotion_trigger)."""
    app = _make_app()
    ctx = _make_ctx(app)

    with pytest.MonkeyPatch.context() as m:
        fire_calls = []
        original_fire = None

        import mcp_server.tools_layer as tl
        original_fire = tl._fire_hook

        def tracking_fire(hook_name, layer, context):
            fire_calls.append(hook_name)
            return original_fire(hook_name, layer, context)

        m.setattr(tl, "_fire_hook", tracking_fire)

        await memory_remember(
            layer="user", user_id="e2e_hooks", key="e2e_hook_test",
            value="test value", importance=0.5, ctx=ctx,
        )

        assert "message_received" in fire_calls
        assert "emotion_trigger" in fire_calls


# ═══════════════════════════════════════════════════════════════
# memory_recall — full logic path
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_recall_returns_stored_data():
    """recall should return data stored by remember."""
    app = _make_app()
    ctx = _make_ctx(app)

    await memory_remember(
        layer="user", user_id="e2e_recall", key="e2e_lang",
        value="Python", importance=0.7, ctx=ctx,
    )
    result = await memory_recall(
        layer="user", user_id="e2e_recall", query="e2e_lang", ctx=ctx,
    )
    assert len(result["results"]) > 0
    assert any("Python" in str(r) for r in result["results"])


@pytest.mark.asyncio
async def test_recall_empty_returns_empty():
    """recall with no matching data returns empty results."""
    app = _make_app()
    ctx = _make_ctx(app)

    result = await memory_recall(
        layer="user", user_id="e2e_empty_xyz", query="nonexistent_xyz_abc", ctx=ctx,
    )
    assert result["results"] == []


# ═══════════════════════════════════════════════════════════════
# memory_forget — full logic path
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_forget_removes_data():
    """forget should remove the key from L4."""
    app = _make_app()
    ctx = _make_ctx(app)

    await memory_remember(
        layer="user", user_id="e2e_forget", key="e2e_temp",
        value="temporary", importance=0.5, ctx=ctx,
    )
    result = await memory_forget(
        layer="user", user_id="e2e_forget", key="e2e_temp", ctx=ctx,
    )
    assert result.get("deleted") is True

    # Verify data is gone
    mem = app.mm.user_memory("e2e_forget")
    entry = await mem.l4.get("e2e_forget", "e2e_temp")
    assert entry is None


# ═══════════════════════════════════════════════════════════════
# memory_session_start / end — full logic path
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_session_lifecycle():
    """session_start → session_end creates and closes a session."""
    app = _make_app()
    ctx = _make_ctx(app)

    start_result = await memory_session_start(
        layer="user", user_id="e2e_sess", ctx=ctx,
    )
    assert "session_id" in start_result
    session_id = start_result["session_id"]

    end_result = await memory_session_end(
        layer="user", user_id="e2e_sess", session_id=session_id,
        summary="Test session complete", ctx=ctx,
    )
    assert end_result["status"] == "ok"


# ═══════════════════════════════════════════════════════════════
# memory_episode_save / recall — full logic path
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_episode_save_and_recall():
    """episode_save → episode_recall retrieves same data."""
    app = _make_app()
    ctx = _make_ctx(app)

    save_result = await memory_episode_save(
        layer="user", user_id="e2e_epi",
        summary="Met friend for coffee", weight=0.7,
        tags=["social", "meeting"], ctx=ctx,
    )
    assert "episode_id" in save_result

    recall_result = await memory_episode_recall(
        layer="user", user_id="e2e_epi", ctx=ctx,
    )
    assert len(recall_result["episodes"]) > 0


# ═══════════════════════════════════════════════════════════════
# memory_graph_add / query — full logic path
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_graph_add_and_query():
    """graph_add → graph_query retrieves same node."""
    app = _make_app()
    ctx = _make_ctx(app)

    add_result = await memory_graph_add(
        layer="user", user_id="e2e_graph",
        content="Python is great for AI", node_type="fact",
        tags=["python", "ai"], ctx=ctx,
    )
    assert "node_id" in add_result

    query_result = await memory_graph_query(
        layer="user", user_id="e2e_graph",
        node_type="fact", ctx=ctx,
    )
    assert len(query_result["nodes"]) > 0


# ═══════════════════════════════════════════════════════════════
# memory_stats — full logic path
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_stats_after_operations():
    """stats should reflect actual data after operations."""
    app = _make_app()
    ctx = _make_ctx(app)

    await memory_remember(
        layer="user", user_id="e2e_stats", key="e2e_k1",
        value="v1", importance=0.5, ctx=ctx,
    )
    result = await memory_stats(layer="user", user_id="e2e_stats", ctx=ctx)
    assert isinstance(result, dict)
    assert "l4_facts" in result
    assert result["l4_facts"] >= 1


# ═══════════════════════════════════════════════════════════════
# memory_context_inject — full logic path
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_context_inject_after_remember():
    """context_inject should include recently stored facts."""
    app = _make_app()
    ctx = _make_ctx(app)

    await memory_remember(
        layer="user", user_id="e2e_ctx", key="e2e_fav_color",
        value="blue", importance=0.7, ctx=ctx,
    )
    result = await memory_context_inject(
        layer="user", user_id="e2e_ctx", ctx=ctx,
    )
    assert isinstance(result, dict)
    assert any(k in result for k in ["l4_facts", "context", "facts"])
