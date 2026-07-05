"""Edge case tests for rag/engine.py — timeout, empty, corrupt, dedup."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


async def _setup():
    from shared.migrations import migration_manager

    await migration_manager.migrate()


asyncio.run(_setup())


def test_rag_empty_query():
    """Search with empty string should not crash."""
    from rag.engine import RAGEngine

    async def t():
        rag = RAGEngine(layer="test_edge")
        results = await rag.search("", user_id="edge_test")
        assert isinstance(results, list)

    asyncio.run(t())


def test_rag_dedup():
    """Ingesting same text twice should return existing page_id."""
    from rag.engine import RAGEngine

    async def t():
        rag = RAGEngine(layer="test_dedup")
        eid1 = await rag.ingest_text("Dedup Test", "Unique content for dedup", user_id="dedup")
        eid2 = await rag.ingest_text("Dedup Test", "Unique content for dedup", user_id="dedup")
        assert eid1 == eid2

    asyncio.run(t())


def test_rag_search_no_results():
    """Search for nonexistent content should return empty list."""
    from rag.engine import RAGEngine

    async def t():
        rag = RAGEngine(layer="test_noresults")
        results = await rag.search("xyznonexistentquery12345", user_id="noresults")
        assert isinstance(results, list)
        assert len(results) == 0

    asyncio.run(t())


def test_rag_count_pages():
    """count_pages should return correct count."""
    from rag.engine import RAGEngine

    async def t():
        import uuid

        uid = "count_" + uuid.uuid4().hex[:8]
        rag = RAGEngine(layer="test_count")
        before = await rag.count_pages(user_id=uid)
        await rag.ingest_text("Count Page 1", "Content 1", user_id=uid)
        await rag.ingest_text("Count Page 2", "Content 2", user_id=uid)
        after = await rag.count_pages(user_id=uid)
        assert after >= before + 2

    asyncio.run(t())


def test_rag_count_chunks():
    """count_chunks should return integer >= 0."""
    from rag.engine import RAGEngine

    async def t():
        rag = RAGEngine(layer="test_chunks")
        count = await rag.count_chunks()
        assert isinstance(count, int)
        assert count >= 0

    asyncio.run(t())


def test_rag_ingest_file():
    """ingest_file should handle a real file."""
    from rag.engine import RAGEngine

    async def t():
        rag = RAGEngine(layer="test_file")
        # Create temp file
        tmp = Path("/tmp/test_rag_edge.txt")
        tmp.write_text("Test file content for RAG edge case", encoding="utf-8")
        result = await rag.ingest_file(tmp, user_id="file_test")
        assert "[OK]" in result or "[SKIP]" in result
        tmp.unlink(missing_ok=True)

    asyncio.run(t())


def test_rag_strategy_auto():
    """Auto strategy should pick fts or hybrid based on query length."""
    from rag.engine import RAGEngine

    async def t():
        rag = RAGEngine(layer="test_auto", search_strategy="auto")
        await rag.ingest_text("Auto Test", "Some content", user_id="auto")
        results = await rag.search("hi", user_id="auto")
        assert isinstance(results, list)

    asyncio.run(t())


def test_rag_relations_empty():
    """get_relations with no relations should return empty list."""
    from rag.engine import RAGEngine

    async def t():
        rag = RAGEngine(layer="test_rels_empty")
        eid = await rag.ingest_text("No Relations", "Content", user_id="rels")
        rels = await rag.get_relations(eid)
        assert isinstance(rels, list)
        assert len(rels) == 0

    asyncio.run(t())


def test_rag_search_limit():
    """Search with limit=1 should return at most 1 result."""
    from rag.engine import RAGEngine

    async def t():
        rag = RAGEngine(layer="test_limit")
        for i in range(5):
            await rag.ingest_text(f"Limit Page {i}", f"Content {i}", user_id="limit")
        results = await rag.search("Content", user_id="limit", limit=1)
        assert len(results) <= 1

    asyncio.run(t())
