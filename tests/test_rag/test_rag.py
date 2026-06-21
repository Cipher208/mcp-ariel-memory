"""Tests for rag/ module (FTS5, RRF, router, conflict)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_rag_ingest_search():
    from rag.engine import RAGEngine
    rag = RAGEngine(layer="test_rag2")
    eid = rag.ingest_text("Unique Python Guide 2026", "Python is great for AI", user_id="t2")
    assert eid > 0
    results = rag.search("Unique Python", user_id="t2")
    assert len(results) > 0


def test_rag_relations():
    from rag.engine import RAGEngine
    rag = RAGEngine(layer="test_rag")
    eid1 = rag.ingest_text("Page A", "Content A", user_id="t")
    eid2 = rag.ingest_text("Page B", "Content B", user_id="t")
    rag.add_relation(eid1, eid2, "related")
    rels = rag.get_relations(eid1)
    assert len(rels) >= 1


def test_rag_rrf():
    from rag.engine import RAGEngine
    rag = RAGEngine(layer="test_rrf")
    rag.ingest_text("Python Guide", "Python is great for AI", user_id="t")
    rag.ingest_text("Go Guide", "Go is great for microservices", user_id="t")
    results = rag.search_rrf("Python AI", user_id="t", limit=3)
    assert len(results) > 0
    assert results[0]["source"] in ("fts5", "vec", "rrf(fts+vec)")


def test_retrieval_router():
    from rag.router import RetrievalRouter
    r = RetrievalRouter(user_id="t")
    result = r.route("Python docs")
    assert result.strategy is not None


def test_conflict_resolver():
    from rag.conflict import ConflictResolver
    cr = ConflictResolver()
    r1 = cr.check("t", "Test content here")
    assert "is_conflict" in r1
