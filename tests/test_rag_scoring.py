"""Tests for rag/scoring.py — unified scoring module."""

import pytest

from rag.scoring import CorpusStats, ScoredCandidate, Scorer, ScoringWeights


class TestScoringWeights:
    def test_defaults(self):
        w = ScoringWeights()
        assert w.relevance == 1.0
        assert w.novelty == 0.0
        assert w.type_boost == 0.0

    def test_custom(self):
        w = ScoringWeights(relevance=2.0, novelty=0.5, type_boost=0.3)
        assert w.relevance == 2.0
        assert w.novelty == 0.5
        assert w.type_boost == 0.3


class TestScoredCandidate:
    def test_required_fields(self):
        c = ScoredCandidate(
            id=1, page_id=10, title="T", content="C", wiki_type=None, rrf_score=0.5
        )
        assert c.id == 1
        assert c.final_score == 0.0
        assert c.debug == {}

    def test_optional_fields(self):
        c = ScoredCandidate(
            id=1, page_id=10, title="T", content="C",
            wiki_type="error", rrf_score=0.8, bin_score=0.7,
            hamming=120, source="mib", memory_kind="fact",
            degraded=True, novelty=0.3, type_boost=0.12,
        )
        assert c.bin_score == 0.7
        assert c.hamming == 120
        assert c.degraded is True


class TestCorpusStats:
    def test_empty_corpus(self):
        stats = CorpusStats()
        assert stats.prior(1) == 1.0

    def test_new_document(self):
        stats = CorpusStats(total_retrievals=10, doc_retrieval_counts={1: 5})
        assert stats.prior(999) == 0.0

    def test_known_document(self):
        stats = CorpusStats(total_retrievals=10, doc_retrieval_counts={1: 3})
        assert stats.prior(1) == 0.3


class TestScorerRelevance:
    def test_rrf_only(self):
        scorer = Scorer()
        c = ScoredCandidate(id=1, page_id=1, title="T", content="C", wiki_type=None, rrf_score=0.5)
        score = scorer._relevance_score(c)
        assert score == 0.5

    def test_rrf_with_bin(self):
        scorer = Scorer()
        c = ScoredCandidate(
            id=1, page_id=1, title="T", content="C", wiki_type=None,
            rrf_score=0.6, bin_score=0.8,
        )
        score = scorer._relevance_score(c)
        assert abs(score - 0.7) < 1e-9


class TestScorerNovelty:
    def _make_candidate(self, page_id: int) -> ScoredCandidate:
        return ScoredCandidate(id=1, page_id=page_id, title="T", content="C", wiki_type=None, rrf_score=0.5)

    def test_no_stats(self):
        scorer = Scorer()
        c = self._make_candidate(1)
        assert scorer._compute_novelty(c) == 0.0

    def test_new_doc_high_novelty(self):
        stats = CorpusStats(total_retrievals=100, doc_retrieval_counts={2: 50})
        scorer = Scorer(corpus_stats=stats)
        c = self._make_candidate(1)
        # doc 1 has 0 retrievals → prior=0 → surprise=max
        assert scorer._compute_novelty(c) == 1.0

    def test_frequent_doc_low_novelty(self):
        stats = CorpusStats(total_retrievals=100, doc_retrieval_counts={1: 90})
        scorer = Scorer(corpus_stats=stats)
        c = self._make_candidate(1)
        # prior=0.9, surprise = -log2(0.9)/log2(100) ≈ 0.033
        score = scorer._compute_novelty(c)
        assert score < 0.1

    def test_novelty_increases_when_retrieval_count_low(self):
        stats_rare = CorpusStats(total_retrievals=100, doc_retrieval_counts={1: 2})
        stats_frequent = CorpusStats(total_retrievals=100, doc_retrieval_counts={1: 50})
        scorer_rare = Scorer(corpus_stats=stats_rare)
        scorer_frequent = Scorer(corpus_stats=stats_frequent)
        c = self._make_candidate(1)
        assert scorer_rare._compute_novelty(c) > scorer_frequent._compute_novelty(c)

    def test_capped_at_one(self):
        stats = CorpusStats(total_retrievals=2, doc_retrieval_counts={2: 1})
        scorer = Scorer(corpus_stats=stats)
        c = self._make_candidate(1)
        # prior=0, surprise = -log2(0.000001)/log2(2) > 1 → capped to 1.0
        assert scorer._compute_novelty(c) == 1.0


class TestScorerTypeBoost:
    def test_no_type(self):
        scorer = Scorer()
        assert scorer._type_boost(None) == 0.0
        assert scorer._type_boost("") == 0.0

    def test_known_types(self):
        scorer = Scorer()
        assert scorer._type_boost("error") == 0.12
        assert scorer._type_boost("decision") == 0.1
        assert scorer._type_boost("spec") == 0.08
        assert scorer._type_boost("code") == 0.05
        assert scorer._type_boost("note") == 0.02

    def test_unknown_type(self):
        scorer = Scorer()
        assert scorer._type_boost("random") == 0.0


class TestScorerRankSync:
    def test_empty_candidates(self):
        scorer = Scorer()
        result = scorer.rank_sync("query", [], "user1")
        assert result == []

    def test_single_candidate(self):
        scorer = Scorer()
        c = ScoredCandidate(id=1, page_id=1, title="T", content="C", wiki_type=None, rrf_score=0.5)
        result = scorer.rank_sync("query", [c], "user1")
        assert len(result) == 1
        assert result[0].final_score == 0.5
        assert result[0].debug["relevance"] == 0.5

    def test_ordering(self):
        scorer = Scorer()
        c1 = ScoredCandidate(id=1, page_id=1, title="A", content="C", wiki_type=None, rrf_score=0.3)
        c2 = ScoredCandidate(id=2, page_id=2, title="B", content="C", wiki_type=None, rrf_score=0.7)
        result = scorer.rank_sync("query", [c1, c2], "user1")
        assert result[0].id == 2
        assert result[1].id == 1

    def test_novelty_influence(self):
        stats = CorpusStats(total_retrievals=100, doc_retrieval_counts={1: 90, 2: 5})
        scorer = Scorer(weights=ScoringWeights(relevance=1.0, novelty=1.0), corpus_stats=stats)
        c1 = ScoredCandidate(id=1, page_id=1, title="A", content="C", wiki_type=None, rrf_score=0.5)
        c2 = ScoredCandidate(id=2, page_id=2, title="B", content="C", wiki_type=None, rrf_score=0.5)
        result = scorer.rank_sync("query", [c1, c2], "user1")
        # c2 is novel (low prior), should rank higher
        assert result[0].id == 2

    def test_weights_control_blend(self):
        stats = CorpusStats(total_retrievals=100, doc_retrieval_counts={1: 50, 2: 50})
        # High relevance weight, low novelty → relevance dominates
        scorer = Scorer(weights=ScoringWeights(relevance=1.0, novelty=0.1), corpus_stats=stats)
        c1 = ScoredCandidate(id=1, page_id=1, title="A", content="C", wiki_type=None, rrf_score=0.8)
        c2 = ScoredCandidate(id=2, page_id=2, title="B", content="C", wiki_type=None, rrf_score=0.3)
        result = scorer.rank_sync("query", [c1, c2], "user1")
        # relevance 0.8 > 0.3, novelty same → c1 wins
        assert result[0].id == 1

        # High novelty weight, same relevance → novelty decides
        scorer2 = Scorer(weights=ScoringWeights(relevance=1.0, novelty=1.0), corpus_stats=stats)
        c3 = ScoredCandidate(id=3, page_id=1, title="C", content="C", wiki_type=None, rrf_score=0.5)
        c4 = ScoredCandidate(id=4, page_id=2, title="D", content="C", wiki_type=None, rrf_score=0.5)
        result2 = scorer2.rank_sync("query", [c3, c4], "user1")
        # same relevance, same novelty (both 50/100) → tie broken by insertion order
        assert len(result2) == 2

    def test_type_boost_influence(self):
        scorer = Scorer(weights=ScoringWeights(relevance=1.0, novelty=0.0, type_boost=1.0))
        c1 = ScoredCandidate(id=1, page_id=1, title="A", content="C", wiki_type="error", rrf_score=0.5)
        c2 = ScoredCandidate(id=2, page_id=2, title="B", content="C", wiki_type="note", rrf_score=0.5)
        result = scorer.rank_sync("query", [c1, c2], "user1")
        # error (0.12) > note (0.02)
        assert result[0].id == 1


class TestScorerAsync:
    @pytest.mark.asyncio
    async def test_rank_async(self):
        scorer = Scorer()
        c = ScoredCandidate(id=1, page_id=1, title="T", content="C", wiki_type=None, rrf_score=0.5)
        result = await scorer.rank("query", [c], "user1")
        assert len(result) == 1
        assert result[0].final_score == 0.5
