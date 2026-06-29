"""Tests for MultiSourceRAG — unified search across RAG + Wiki."""
import pytest


class FakeRAG:
    """Minimal RAG mock for testing."""

    def __init__(self, results=None):
        self._results = results or []
        self.cm = None

    async def search(self, query, user_id="default", strategy="hybrid", limit=10):
        return self._results[:limit]


class FakeWiki:
    """Minimal Wiki mock for testing."""

    def __init__(self, results=None):
        self._results = results or []

    async def search(self, query, user_id="default", limit=10):
        return self._results[:limit]


class TestMultiSourceRAG:
    def test_empty_sources(self):
        from rag.multi_source import MultiSourceRAG

        m = MultiSourceRAG(FakeRAG(), FakeWiki())
        import asyncio
        result = asyncio.run(m.search("test"))
        assert result == []

    def test_rag_only(self):
        from rag.multi_source import MultiSourceRAG

        rag = FakeRAG([{"id": 1, "title": "RAG result", "content": "content", "score": 0.8, "source": "fts"}])
        m = MultiSourceRAG(rag, FakeWiki())
        import asyncio
        result = asyncio.run(m.search("test", include_wiki=False))
        assert len(result) == 1
        assert result[0]["source"] != "wiki_fts"

    def test_wiki_only(self):
        from rag.multi_source import MultiSourceRAG

        wiki = FakeWiki([{"entry_id": 1, "title": "Wiki result", "content": "wiki content", "wiki_type": "diary"}])
        m = MultiSourceRAG(FakeRAG(), wiki)
        import asyncio
        result = asyncio.run(m.search("test", include_rag=False))
        assert len(result) == 1
        assert result[0]["source"] == "wiki_fts"
        assert result[0]["wiki_type"] == "wiki:diary"
        assert result[0]["id"] < 0  # Negative id for wiki

    def test_merge_and_dedup(self):
        from rag.multi_source import MultiSourceRAG

        rag = FakeRAG([{"id": 1, "title": "Same", "content": "Same content here", "score": 0.8}])
        wiki = FakeWiki([{"entry_id": 1, "title": "Same", "content": "Same content here", "wiki_type": "diary"}])
        m = MultiSourceRAG(rag, wiki)
        import asyncio
        result = asyncio.run(m.search("test"))
        assert len(result) == 1  # Deduped

    def test_rerank_by_score(self):
        from rag.multi_source import MultiSourceRAG

        rag = FakeRAG([{"id": 1, "title": "Low", "content": "a", "score": 0.3}])
        wiki = FakeWiki([{"entry_id": 1, "title": "High", "content": "b", "rank": 0.9}])
        m = MultiSourceRAG(rag, wiki)
        import asyncio
        result = asyncio.run(m.search("test"))
        assert result[0]["title"] == "High"  # Higher score first

    def test_respects_limit(self):
        from rag.multi_source import MultiSourceRAG

        rag = FakeRAG([{"id": i, "title": f"t{i}", "content": f"c{i}", "score": 0.5} for i in range(20)])
        m = MultiSourceRAG(rag, FakeWiki())
        import asyncio
        result = asyncio.run(m.search("test", limit=5))
        assert len(result) == 5

    def test_rag_error_handled(self):
        from rag.multi_source import MultiSourceRAG

        class FailingRAG:
            cm = None
            async def search(self, **kwargs):
                raise RuntimeError("DB error")

        m = MultiSourceRAG(FailingRAG(), FakeWiki([{"entry_id": 1, "title": "W", "content": "C"}]))
        import asyncio
        result = asyncio.run(m.search("test"))
        assert len(result) == 1  # Wiki still works

    def test_wiki_error_handled(self):
        from rag.multi_source import MultiSourceRAG

        class FailingWiki:
            async def search(self, **kwargs):
                raise RuntimeError("Wiki error")

        m = MultiSourceRAG(FakeRAG([{"id": 1, "title": "R", "content": "C"}]), FailingWiki())
        import asyncio
        result = asyncio.run(m.search("test"))
        assert len(result) == 1  # RAG still works
