"""Tests for shared/ module — async."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_dream_buffer():
    from shared.dream_buffer import DreamBuffer

    async def t():
        db = DreamBuffer()
        await db.add("test_sh", "s1", "msg", 0.5)
        assert await db.count("test_sh") >= 1
        await db.cleanup_old(max_age_hours=0, max_count=0)

    asyncio.run(t())


def test_archived_memories():
    from shared.archived_memories import ArchivedMemories

    async def t():
        am = ArchivedMemories()
        await am.archive("test_sh", "Old memory", importance=0.2, reason="test")
        archived = await am.get_archived("test_sh")
        assert len(archived) >= 1

    asyncio.run(t())


def test_embedding_cache():
    from shared.embeddings import EmbeddingCache

    async def t():
        ec = EmbeddingCache()
        emb = await ec.embed_single("test")
        assert len(emb) == 384

    asyncio.run(t())


def test_metrics():
    from shared.metrics import metrics

    metrics.inc("test_counter")
    prom = metrics.render_prometheus()
    assert "test_counter" in prom


def test_middleware():
    from shared.middleware import MiddlewareContext, MiddlewarePipeline, ValidationMiddleware

    async def t():
        p = MiddlewarePipeline()
        p.add(ValidationMiddleware())
        ctx = MiddlewareContext(tool_name="test", user_id="u", args={"key": "k", "value": "v"})
        return await p.execute(ctx, lambda c: {"ok": True})

    r = asyncio.run(t())
    assert r["ok"] is True
