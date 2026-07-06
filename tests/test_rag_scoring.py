"""Tests for rag/scoring.py — unified scoring module — parametrized."""

import pytest

from rag.scoring import CorpusStats, ScoredCandidate, Scorer, ScoringWeights


@pytest.mark.parametrize("kwargs,expected", [
    ({"relevance": 1.0, "novelty": 0.0, "type_boost": 0.0}, {"relevance": 1.0, "novelty": 0.0}),
    ({"relevance": 2.0, "novelty": 0.5, "type_boost": 0.3}, {"relevance": 2.0, "novelty": 0.5}),
])
def test_scoring_weights(kwargs, expected):
    w = ScoringWeights(**kwargs)
    for k, v in expected.items():
        assert getattr(w, k) == v


def test_scored_candidate_fields():
    c = ScoredCandidate(id=1, page_id=10, title="T", content="C", wiki_type=None, rrf_score=0.5)
    assert c.id == 1
    assert c.final_score == 0.0
    assert c.debug == {}

    c2 = ScoredCandidate(
        id=2, page_id=10, title="T", content="C", wiki_type="error",
        rrf_score=0.8, bin_score=0.7, hamming=120, source="mib",
        memory_kind="fact", degraded=True, novelty=0.3, type_boost=0.12,
    )
    assert c2.bin_score == 0.7
    assert c2.hamming == 120
    assert c2.degraded is True


@pytest.mark.parametrize("doc_id,total,count_map,expected_prior", [
    (1, 0, {}, 1.0),           # empty corpus → prior=1
    (999, 10, {1: 5}, 0.0),    # new doc → prior=0
    (1, 10, {1: 3}, 0.3),      # known doc → prior=count/total
])
def test_corpus_stats(doc_id, total, count_map, expected_prior):
    stats = CorpusStats(total_retrievals=total, doc_retrieval_counts=count_map)
    assert stats.prior(doc_id) == pytest.approx(expected_prior, abs=1e-9)


@pytest.mark.parametrize("rrf,bin_score,expected", [
    (0.5, None, 0.5),
    (0.6, 0.8, 0.7),
])
def test_relevance_score(rrf, bin_score, expected):
    scorer = Scorer()
    c = ScoredCandidate(id=1, page_id=1, title="T", content="C", wiki_type=None, rrf_score=rrf, bin_score=bin_score)
    score = scorer._relevance_score(c)
    assert score == pytest.approx(expected, abs=1e-9)


@pytest.mark.parametrize("doc_retrievals,total_retrievals,other_retrievals,expect_high", [
    (0, 100, {2: 50}, True),    # new doc → high novelty
    (90, 100, {}, False),        # frequent doc → low novelty
    (2, 100, {}, True),          # rare doc → high novelty
])
def test_novelty(doc_retrievals, total_retrievals, other_retrievals, expect_high):
    stats = CorpusStats(total_retrievals=total_retrievals, doc_retrieval_counts=other_retrievals)
    scorer = Scorer(corpus_stats=stats)
    c = ScoredCandidate(id=1, page_id=1, title="T", content="C", wiki_type=None, rrf_score=0.5)
    # We need to set doc 1's retrieval count manually
    if doc_retrievals > 0:
        stats.doc_retrieval_counts[1] = doc_retrievals
    novelty = scorer._compute_novelty(c)
    if expect_high:
        assert novelty > 0.1
    else:
        assert novelty < 0.1


def test_novelty_capped_at_one():
    stats = CorpusStats(total_retrievals=2, doc_retrieval_counts={2: 1})
    scorer = Scorer(corpus_stats=stats)
    c = ScoredCandidate(id=1, page_id=1, title="T", content="C", wiki_type=None, rrf_score=0.5)
    assert scorer._compute_novelty(c) == 1.0


def test_novelty_increases_when_rare():
    stats_rare = CorpusStats(total_retrievals=100, doc_retrieval_counts={1: 2})
    stats_frequent = CorpusStats(total_retrievals=100, doc_retrieval_counts={1: 50})
    scorer_rare = Scorer(corpus_stats=stats_rare)
    scorer_frequent = Scorer(corpus_stats=stats_frequent)
    c = ScoredCandidate(id=1, page_id=1, title="T", content="C", wiki_type=None, rrf_score=0.5)
    assert scorer_rare._compute_novelty(c) > scorer_frequent._compute_novelty(c)


@pytest.mark.parametrize("wiki_type,expected", [
    (None, 0.0),
    ("", 0.0),
    ("error", 0.12),
    ("decision", 0.1),
    ("spec", 0.08),
    ("code", 0.05),
    ("note", 0.02),
    ("random", 0.0),
])
def test_type_boost(wiki_type, expected):
    scorer = Scorer()
    assert scorer._type_boost(wiki_type) == expected


def test_rank_sync_ordering():
    scorer = Scorer()
    c1 = ScoredCandidate(id=1, page_id=1, title="A", content="C", wiki_type=None, rrf_score=0.3)
    c2 = ScoredCandidate(id=2, page_id=2, title="B", content="C", wiki_type=None, rrf_score=0.7)
    result = scorer.rank_sync("query", [c1, c2], "user1")
    assert result[0].id == 2
    assert result[1].id == 1


def test_rank_sync_novelty_influence():
    stats = CorpusStats(total_retrievals=100, doc_retrieval_counts={1: 90, 2: 5})
    scorer = Scorer(weights=ScoringWeights(relevance=1.0, novelty=1.0), corpus_stats=stats)
    c1 = ScoredCandidate(id=1, page_id=1, title="A", content="C", wiki_type=None, rrf_score=0.5)
    c2 = ScoredCandidate(id=2, page_id=2, title="B", content="C", wiki_type=None, rrf_score=0.5)
    result = scorer.rank_sync("query", [c1, c2], "user1")
    assert result[0].id == 2


def test_rank_sync_type_boost():
    scorer = Scorer(weights=ScoringWeights(relevance=1.0, novelty=0.0, type_boost=1.0))
    c1 = ScoredCandidate(id=1, page_id=1, title="A", content="C", wiki_type="error", rrf_score=0.5)
    c2 = ScoredCandidate(id=2, page_id=2, title="B", content="C", wiki_type="note", rrf_score=0.5)
    result = scorer.rank_sync("query", [c1, c2], "user1")
    assert result[0].id == 1


@pytest.mark.asyncio
async def test_rank_async():
    scorer = Scorer()
    c = ScoredCandidate(id=1, page_id=1, title="T", content="C", wiki_type=None, rrf_score=0.5)
    result = await scorer.rank("query", [c], "user1")
    assert len(result) == 1
    assert result[0].final_score == 0.5
