"""
Shared hook utilities — eliminates duplication between agent and user hooks.
"""

import asyncio
import concurrent.futures
import logging
import threading
from typing import Any

from lifecycle.consolidation import ConsolidationEngine
from lifecycle.forgetting import ForgettingSystem
from rag.conflict import ConflictResolver
from rag.router import RetrievalRouter

logger = logging.getLogger(__name__)

# Lock to prevent concurrent SQLite access from run_async
_db_lock = threading.Lock()

# Module-level executor to avoid creating a new pool on every run_async call
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def run_async(coro):
    """Run async coroutine from sync context, handling running event loops.

    Uses threading.Lock to prevent concurrent SQLite access.
    """
    with _db_lock:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            future = _executor.submit(asyncio.run, coro)
            return future.result()
        else:
            return asyncio.run(coro)


def forgetting_ritual(ctx: dict[str, Any]) -> dict[str, Any]:
    fs = ForgettingSystem()
    return fs.cleanup()


def conflict_resolver(ctx: dict[str, Any], user_id: str) -> dict[str, Any]:
    content = ctx.get("content", "")
    resolver = ConflictResolver()
    return resolver.check(user_id, content)


def auto_context(
    ctx: dict[str, Any], user_id: str, layer: str | None = None
) -> dict[str, Any]:
    query = ctx.get("query", "")
    if layer is not None:
        router = RetrievalRouter(layer=layer, user_id=user_id)
    else:
        router = RetrievalRouter(user_id=user_id)
    result = router.route(query)
    return {"context": result.context, "strategy": result.strategy.value}


def retrieval_router(
    ctx: dict[str, Any],
    user_id: str,
    layer: str | None = None,
    include_count: bool = False,
) -> dict[str, Any]:
    query = ctx.get("query", "")
    if layer is not None:
        router = RetrievalRouter(layer=layer, user_id=user_id)
    else:
        router = RetrievalRouter(user_id=user_id)
    result = router.route(query)
    resp: dict[str, Any] = {
        "strategy": result.strategy.value,
        "confidence": result.confidence,
    }
    if include_count:
        resp["count"] = len(result.context)
    return resp


def consolidation(
    ctx: dict[str, Any],
    user_id: str,
    min_importance: float | None = None,
    action_key: str = "consolidated",
) -> dict[str, Any]:
    staging = ctx.get("staging_items", [])
    engine = ConsolidationEngine()
    if min_importance is not None:
        result = engine.consolidate_staging(user_id, staging, min_importance=min_importance)
    else:
        result = engine.consolidate_staging(user_id, staging)
    return {"action": action_key, **result}
