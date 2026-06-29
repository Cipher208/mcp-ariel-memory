"""Layer tools — unified user/agent memory operations.

All tools accept a `layer` parameter: "user" or "agent".
Rate limiting is applied to all write operations.
Caching is applied to context_inject and recall.
"""

import hashlib
import time

from mcp.server.fastmcp import Context

from shared.metrics import metrics


def _get_ctx(ctx: Context):
    from mcp_server.server import _get_ctx as _g

    return _g(ctx)


def _get_memory(app, layer: str, user_id: str):
    if layer == "agent":
        return app.mm.agent_memory(user_id)
    return app.mm.user_memory(user_id)


def _get_graph(app, layer: str):
    if layer == "agent":
        return app.agent_graph
    return app.user_graph


def _get_wiki(app, layer: str):
    if layer == "agent":
        return app.agent_wiki
    return app.user_wiki


def _get_hooks(app, layer: str):
    if layer == "agent":
        return app.agent_hooks
    return app.user_hooks


async def _check_rate_limit(app, user_id: str) -> dict | None:
    """Check rate limit. Returns error dict if exceeded, None if ok."""
    try:
        result = await app.rate_limiter.check(user_id)
        if not result.get("allowed", True):
            return {
                "error": "rate_limit_exceeded",
                "remaining": result.get("remaining", 0),
                "reset_in": result.get("reset_in", 60),
            }
    except Exception:
        pass
    return None


# Context cache: {key: (timestamp, data)}
_context_cache: dict[str, tuple[float, dict]] = {}
_CONTEXT_CACHE_TTL = 30  # seconds


def _get_cache_key(layer: str, user_id: str) -> str:
    return f"{layer}:{user_id}"


def _get_cached(key: str) -> dict | None:
    if key in _context_cache:
        ts, data = _context_cache[key]
        if time.time() - ts < _CONTEXT_CACHE_TTL:
            return data
    return None


def _set_cached(key: str, data: dict) -> None:
    _context_cache[key] = (time.time(), data)


# Recall cache
_recall_cache: dict[str, tuple[float, list]] = {}
_RECALL_CACHE_TTL = 10  # seconds


def _get_recall_cache(query: str, user_id: str, layer: str, limit: int) -> list | None:
    key = hashlib.md5(f"{layer}:{user_id}:{query}:{limit}".encode()).hexdigest()
    if key in _recall_cache:
        ts, results = _recall_cache[key]
        if time.time() - ts < _RECALL_CACHE_TTL:
            return results
    return None


def _set_recall_cache(query: str, user_id: str, layer: str, limit: int, results: list) -> None:
    key = hashlib.md5(f"{layer}:{user_id}:{query}:{limit}".encode()).hexdigest()
    _recall_cache[key] = (time.time(), results)


def register_tools(mcp):
    @mcp.tool()
    async def memory_remember(
        layer: str = "user",
        user_id: str = "default",
        key: str = "",
        value: str = "",
        importance: float = 0.5,
        ctx: Context = None,
    ) -> dict:
        """Save a fact to long-term memory (L4 CoreMemory).

        Args:
            layer: "user" for user facts, "agent" for agent identity
            user_id: User identifier
            key: Fact key (e.g. "name", "language", "principle")
            value: Fact value
            importance: Importance score 0.0-1.0 (default 0.5)
        """
        app = _get_ctx(ctx)
        metrics.inc("tool_calls")
        metrics.inc("tool_remember")

        rate_limit = await _check_rate_limit(app, user_id)
        if rate_limit:
            return rate_limit

        hooks = _get_hooks(app, layer)
        gate = hooks._importance_gate({"text": value})
        if gate.get("bypass"):
            return {"status": "skipped", "reason": "below_importance_threshold"}

        mem = _get_memory(app, layer, user_id)

        if layer == "agent":
            import asyncio

            entry_id, node_id = await asyncio.gather(
                mem.remember(key, value, importance),
                _get_graph(app, layer).add_node(
                    user_id,
                    value,
                    "error_analysis" if "error" in key.lower() else "decision_log" if "decision" in key.lower() else "agent_fact",
                    ["error_pattern"] if "error" in key.lower() else ["decided_because"] if "decision" in key.lower() else [],
                    importance,
                ),
            )
            # Invalidate context cache
            _context_cache.pop(_get_cache_key(layer, user_id), None)
            return {"status": "ok", "entry_id": entry_id, "graph_node_id": node_id}

        entry_id = await mem.remember(key, value, importance)
        should_save, emotion_reason, emotion_weight = app.emotion_trigger.should_save(value)
        if should_save:
            await mem.l3.save(user_id, "%s=%s" % (key, value[:50]), emotion_weight, [emotion_reason])

        _context_cache.pop(_get_cache_key(layer, user_id), None)
        return {"status": "ok", "entry_id": entry_id}

    @mcp.tool()
    async def memory_recall(
        layer: str = "user",
        user_id: str = "default",
        query: str = "",
        limit: int = 10,
        ctx: Context = None,
    ) -> dict:
        """Search memory across L3 (episodes) and L4 (facts).

        Args:
            layer: "user" or "agent"
            user_id: User identifier
            query: Search query
            limit: Max results (default 10)
        """
        app = _get_ctx(ctx)
        metrics.inc("tool_calls")
        metrics.inc("tool_recall")

        cached = _get_recall_cache(query, user_id, layer, limit)
        if cached is not None:
            return {"results": cached, "count": len(cached), "cached": True}

        results = await _get_memory(app, layer, user_id).recall(query, limit)
        _set_recall_cache(query, user_id, layer, limit, results)
        return {"results": results, "count": len(results)}

    @mcp.tool()
    async def memory_forget(
        layer: str = "user",
        user_id: str = "default",
        key: str = "",
        ctx: Context = None,
    ) -> dict:
        """Delete a fact from L4 memory.

        Args:
            layer: "user" or "agent"
            user_id: User identifier
            key: Fact key to delete
        """
        app = _get_ctx(ctx)
        metrics.inc("tool_calls")
        metrics.inc("tool_forget")

        rate_limit = await _check_rate_limit(app, user_id)
        if rate_limit:
            return rate_limit

        deleted = await _get_memory(app, layer, user_id).forget(key)
        _context_cache.pop(_get_cache_key(layer, user_id), None)
        return {"deleted": deleted}

    @mcp.tool()
    async def memory_session_start(
        layer: str = "user",
        user_id: str = "default",
        ctx: Context = None,
    ) -> dict:
        """Start a new memory session.

        Args:
            layer: "user" or "agent"
            user_id: User identifier
        """
        app = _get_ctx(ctx)
        metrics.inc("tool_calls")
        metrics.inc("tool_session_start")

        rate_limit = await _check_rate_limit(app, user_id)
        if rate_limit:
            return rate_limit

        session_id = await _get_memory(app, layer, user_id).l2.create_session(user_id)
        return {"session_id": session_id}

    @mcp.tool()
    async def memory_session_end(
        layer: str = "user",
        user_id: str = "default",
        session_id: str = "",
        summary: str = "",
        ctx: Context = None,
    ) -> dict:
        """End a session and save summary.

        Args:
            layer: "user" or "agent"
            user_id: User identifier
            session_id: Session ID from session_start
            summary: Session summary
        """
        app = _get_ctx(ctx)
        metrics.inc("tool_calls")
        metrics.inc("tool_session_end")

        rate_limit = await _check_rate_limit(app, user_id)
        if rate_limit:
            return rate_limit

        await _get_memory(app, layer, user_id).l2.close_session(session_id, summary)
        return {"status": "ok"}

    @mcp.tool()
    async def memory_episode_save(
        layer: str = "user",
        user_id: str = "default",
        summary: str = "",
        weight: float = 0.5,
        tags: list[str] | None = None,
        ctx: Context = None,
    ) -> dict:
        """Save an episode to L3 episodic memory.

        Args:
            layer: "user" or "agent"
            user_id: User identifier
            summary: Episode description
            weight: Emotional weight 0.0-1.0 (default 0.5)
            tags: Tags (e.g. ["greeting", "decision", "error"])
        """
        app = _get_ctx(ctx)
        metrics.inc("tool_calls")
        metrics.inc("tool_episode_save")

        rate_limit = await _check_rate_limit(app, user_id)
        if rate_limit:
            return rate_limit

        episode_id = await _get_memory(app, layer, user_id).l3.save(user_id, summary, weight, tags)
        _context_cache.pop(_get_cache_key(layer, user_id), None)
        return {"episode_id": episode_id}

    @mcp.tool()
    async def memory_episode_recall(
        layer: str = "user",
        user_id: str = "default",
        tag: str = "",
        limit: int = 10,
        ctx: Context = None,
    ) -> dict:
        """Recall episodes, optionally filtered by tag.

        Args:
            layer: "user" or "agent"
            user_id: User identifier
            tag: Filter by tag (empty = all)
            limit: Max results (default 10)
        """
        app = _get_ctx(ctx)
        metrics.inc("tool_calls")
        metrics.inc("tool_episode_recall")
        mem = _get_memory(app, layer, user_id)
        if tag:
            episodes = await mem.l3.search_by_tag(user_id, tag, limit)
        else:
            episodes = await mem.l3.get_episodes(user_id, limit)
        return {"episodes": [{"id": e.episode_id, "summary": e.summary, "weight": e.emotional_weight} for e in episodes]}

    @mcp.tool()
    async def memory_graph_add(
        layer: str = "user",
        user_id: str = "default",
        content: str = "",
        node_type: str = "fact",
        tags: list[str] | None = None,
        ctx: Context = None,
    ) -> dict:
        """Add a node to the epistemic graph.

        Args:
            layer: "user" or "agent"
            user_id: User identifier
            content: Node content
            node_type: Node type (fact, decision, emotion, error_analysis, etc.)
            tags: Tags
        """
        app = _get_ctx(ctx)
        metrics.inc("tool_calls")
        metrics.inc("tool_graph_add")

        rate_limit = await _check_rate_limit(app, user_id)
        if rate_limit:
            return rate_limit

        node_id = await _get_graph(app, layer).add_node(user_id, content, node_type, tags)
        _context_cache.pop(_get_cache_key(layer, user_id), None)
        return {"node_id": node_id}

    @mcp.tool()
    async def memory_graph_query(
        layer: str = "user",
        user_id: str = "default",
        tag: str = "",
        node_type: str = "",
        limit: int = 20,
        ctx: Context = None,
    ) -> dict:
        """Query the epistemic graph by tag or node type.

        Args:
            layer: "user" or "agent"
            user_id: User identifier
            tag: Filter by tag
            node_type: Filter by type
            limit: Max results
        """
        app = _get_ctx(ctx)
        metrics.inc("tool_calls")
        metrics.inc("tool_graph_query")
        graph = _get_graph(app, layer)
        if tag:
            nodes = await graph.query_by_tag(user_id, tag, limit)
        elif node_type:
            nodes = await graph.query_by_type(user_id, node_type, limit)
        else:
            nodes = []
        return {"nodes": [{"id": n.node_id, "content": n.content, "type": n.node_type, "tags": n.tags} for n in nodes]}

    @mcp.tool()
    async def memory_stats(
        layer: str = "user",
        user_id: str = "default",
        ctx: Context = None,
    ) -> dict:
        """Get memory statistics for a layer.

        Args:
            layer: "user" or "agent"
            user_id: User identifier
        """
        app = _get_ctx(ctx)
        metrics.inc("tool_calls")
        metrics.inc("tool_stats")
        mem = _get_memory(app, layer, user_id)
        wiki = _get_wiki(app, layer)
        graph = _get_graph(app, layer)
        l3_count = await mem.l3.count(user_id)
        return {
            "l1_buffer": mem.l1.size(),
            "l2_sessions": await mem.l2.count_sessions(user_id),
            "l3_episodes": l3_count,
            "l4_facts": await mem.l4.count(user_id),
            "wiki_pages": await wiki.count(),
            "graph_nodes": await graph.count_nodes(user_id),
        }

    @mcp.tool()
    async def memory_context_inject(
        layer: str = "user",
        user_id: str = "default",
        ctx: Context = None,
    ) -> dict:
        """Return compressed summary for prompt injection (L4 top-10 + L3 top-3).

        Args:
            layer: "user" or "agent"
            user_id: User identifier
        """
        metrics.inc("tool_calls")
        metrics.inc("tool_context_inject")

        cache_key = _get_cache_key(layer, user_id)
        cached = _get_cached(cache_key)
        if cached is not None:
            return {**cached, "cached": True}

        app = _get_ctx(ctx)
        mem = _get_memory(app, layer, user_id)
        wiki = _get_wiki(app, layer)

        l4_facts = await mem.l4.get_all(user_id, 10)
        facts_text = "; ".join(["%s=%s" % (f.key, f.value[:30]) for f in l4_facts])

        l3_episodes = await mem.l3.get_episodes(user_id, 3)
        episodes_text = "; ".join(["%s" % e.summary[:50] for e in l3_episodes])

        l1_recent = mem.l1.get_recent(5)
        recent_text = "; ".join(["%s: %s" % (r.role, r.content[:50]) for r in l1_recent])

        wiki_entries = await wiki.list_all(3)
        wiki_text = "; ".join(["[%s] %s" % (w.wiki_type, w.title) for w in wiki_entries])

        context_parts = []
        if facts_text:
            context_parts.append("FACTS: " + facts_text)
        if episodes_text:
            context_parts.append("EPISODES: " + episodes_text)
        if recent_text:
            context_parts.append("RECENT: " + recent_text)
        if wiki_text:
            context_parts.append("WIKI: " + wiki_text)

        result = {
            "context": "\n".join(context_parts),
            "l4_facts_count": len(l4_facts),
            "l3_episodes_count": len(l3_episodes),
            "l1_recent_count": len(l1_recent),
            "wiki_count": len(wiki_entries),
        }
        _set_cached(cache_key, result)
        return result
