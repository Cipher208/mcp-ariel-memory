"""Tests for shared/ module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_cache():
    from shared.cache import MemoryCache
    mc = MemoryCache(max_size=5, ttl=60)
    mc.set("k", "v")
    assert mc.get("k") == "v"
    mc.delete("k")
    assert mc.get("k") is None


def test_dream_buffer():
    from shared.dream_buffer import DreamBuffer
    db = DreamBuffer()
    db.add("test_sh", "s1", "msg", 0.5)
    assert db.count("test_sh") >= 1
    db.cleanup_old(max_age_hours=0, max_count=0)


def test_archived_memories():
    from shared.archived_memories import ArchivedMemories
    am = ArchivedMemories()
    am.archive("test_sh", "Old memory", importance=0.2, reason="test")
    archived = am.get_archived("test_sh")
    assert len(archived) >= 1


def test_embedding_cache():
    from shared.embeddings import EmbeddingCache
    ec = EmbeddingCache()
    emb = ec.embed_single("test")
    assert len(emb) == 384


def test_metrics():
    from shared.metrics import metrics
    metrics.inc("test_counter")
    prom = metrics.render_prometheus()
    assert "test_counter" in prom


def test_middleware():
    from shared.middleware import MiddlewarePipeline, MiddlewareContext, ValidationMiddleware
    p = MiddlewarePipeline()
    p.add(ValidationMiddleware())

    async def test_mw():
        ctx = MiddlewareContext(tool_name="test", user_id="u", args={"key": "k", "value": "v"})
        return await p.execute(ctx, lambda c: {"ok": True})

    import asyncio
    r = asyncio.run(test_mw())
    assert r["ok"] is True
