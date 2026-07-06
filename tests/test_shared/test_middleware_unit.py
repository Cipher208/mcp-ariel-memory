"""Tests for shared/middleware.py — actual API."""

import asyncio
from shared.middleware import (
    MiddlewareContext,
    ImportanceGateMiddleware,
    DedupMiddleware,
    ValidationMiddleware,
    AuditMiddleware,
    MiddlewarePipeline,
)


def test_middleware_context_defaults():
    ctx = MiddlewareContext()
    assert ctx.tool_name == ""
    assert ctx.user_id == "default"
    assert ctx.blocked is False


def test_importance_gate_blocks_low():
    gate = ImportanceGateMiddleware()
    ctx = MiddlewareContext(args={"value": "hi"}, tool_name="memory_user_remember")

    async def handler(c):
        return {"ok": True}

    result = asyncio.run(gate.process(ctx, handler))
    assert ctx.blocked is True


def test_importance_gate_allows_high():
    gate = ImportanceGateMiddleware()
    ctx = MiddlewareContext(
        args={
            "value": "This is a critical and important decision about our architecture that affects production systems and requires immediate attention"
        },
        tool_name="memory_user_remember",
    )

    async def handler(c):
        return {"ok": True}

    result = asyncio.run(gate.process(ctx, handler))
    assert ctx.blocked is False


def test_validation_blocks_empty_user():
    val = ValidationMiddleware()
    ctx = MiddlewareContext(user_id="", tool_name="memory_remember")

    async def handler(c):
        return {"ok": True}

    asyncio.run(val.process(ctx, handler))
    assert ctx.blocked is True


def test_validation_blocks_missing_key():
    val = ValidationMiddleware()
    ctx = MiddlewareContext(user_id="u1", tool_name="memory_user_remember", args={})

    async def handler(c):
        return {"ok": True}

    asyncio.run(val.process(ctx, handler))
    assert ctx.blocked is True


def test_validation_allows_valid():
    val = ValidationMiddleware()
    ctx = MiddlewareContext(user_id="u1", tool_name="memory_user_remember", args={"key": "k"})

    async def handler(c):
        return {"ok": True}

    asyncio.run(val.process(ctx, handler))
    assert ctx.blocked is False


def test_dedup_catches_duplicates():
    dedup = DedupMiddleware()
    ctx1 = MiddlewareContext(tool_name="test_tool", user_id="u1", args={"k": "v"})

    async def handler(c):
        return {"ok": True}

    r1 = asyncio.run(dedup.process(ctx1, handler))
    assert r1 == {"ok": True}

    ctx2 = MiddlewareContext(tool_name="test_tool", user_id="u1", args={"k": "v"})
    r2 = asyncio.run(dedup.process(ctx2, handler))
    assert ctx2.metadata.get("deduped") is True


def test_pipeline_runs():
    pipe = MiddlewarePipeline()

    class CountMiddleware:
        name = "count"

        async def process(self, ctx, next_fn):
            ctx.metadata["count"] = True
            return await next_fn(ctx)

    pipe.add(CountMiddleware())

    async def handler(ctx):
        return {"ok": True}

    ctx = MiddlewareContext()
    result = asyncio.run(pipe.execute(ctx, handler))
    assert result == {"ok": True}
    assert ctx.metadata.get("count") is True


def test_audit_sets_metadata():
    audit = AuditMiddleware()
    ctx = MiddlewareContext()

    async def handler(c):
        return {"ok": True}

    asyncio.run(audit.process(ctx, handler))
    assert "elapsed" in ctx.metadata
