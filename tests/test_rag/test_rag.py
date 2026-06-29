"""Tests for rag/ module — async."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# Ensure migrations run
async def _setup():
    from shared.migrations import migration_manager

    await migration_manager.migrate()


asyncio.run(_setup())


def test_rag_ingest_search():
    from rag.engine import RAGEngine

    async def t():
        rag = RAGEngine(layer="test_rag2")
        eid = await rag.ingest_text("Unique Python Guide 2026", "Python is great for AI", user_id="t2")
        assert eid > 0
        results = await rag.search("Unique Python", user_id="t2")
        assert len(results) > 0

    asyncio.run(t())


def test_rag_relations():
    from rag.engine import RAGEngine

    async def t():
        rag = RAGEngine(layer="test_rag_r")
        eid1 = await rag.ingest_text("Page A", "Content A", user_id="t")
        eid2 = await rag.ingest_text("Page B", "Content B", user_id="t")
        await rag.add_relation(eid1, eid2, "related")
        rels = await rag.get_relations(eid1)
        assert len(rels) >= 1

    asyncio.run(t())


def test_rag_hybrid():
    from rag.engine import RAGEngine

    async def t():
        rag = RAGEngine(layer="test_rrf2")
        await rag.ingest_text("A", "Content A", user_id="t")
        await rag.ingest_text("B", "Content B", user_id="t")
        results = await rag.search("Content", user_id="t", strategy="hybrid", limit=3)
        assert len(results) > 0

    asyncio.run(t())


def test_retrieval_router():
    from rag.router import RetrievalRouter

    async def t():
        r = RetrievalRouter(user_id="t")
        result = await r.route("Python docs")
        assert result.strategy is not None

    asyncio.run(t())


def test_conflict_resolver():
    from rag.conflict import ConflictResolver

    async def t():
        cr = ConflictResolver()
        r = await cr.check("t", "Test content here")
        assert "is_conflict" in r

    asyncio.run(t())
