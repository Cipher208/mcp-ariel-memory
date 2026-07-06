"""Property-based tests using Hypothesis.

Tests mathematical invariants and roundtrip properties that must hold
for ALL valid inputs, not just hand-picked examples.
"""

import threading
import time

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

# ── Fixed-dimension strategies (avoid assume() filtering) ──

DIM = 32  # small dimension for fast tests
st_dim_vec = st.lists(st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False), min_size=DIM, max_size=DIM)
st_short_text = st.text(min_size=1, max_size=200, alphabet=st.characters(blacklist_categories=("Cs",)))


# ═══════════════════════════════════════════════════════════════
#  rag/conflict.py — similarity function invariants
# ═══════════════════════════════════════════════════════════════

from rag.conflict import bm25_pair_similarity, char_ngram_jaccard, smart_similarity


class TestSimilarityProperties:
    @given(a=st_short_text, b=st_short_text)
    @settings(max_examples=200)
    def test_similarity_range(self, a, b):
        for fn in (bm25_pair_similarity, char_ngram_jaccard, smart_similarity):
            score = fn(a, b)
            assert 0.0 <= score <= 1.0, f"{fn.__name__} returned {score}"

    @given(a=st_short_text)
    @settings(max_examples=100)
    def test_self_similarity_non_negative(self, a):
        assume(len(a) >= 3)
        assert bm25_pair_similarity(a, a) >= 0.0
        assert char_ngram_jaccard(a, a) >= 0.0
        assert smart_similarity(a, a) >= 0.0

    @given(a=st_short_text, b=st_short_text)
    @settings(max_examples=100)
    def test_symmetry(self, a, b):
        assert abs(bm25_pair_similarity(a, b) - bm25_pair_similarity(b, a)) < 1e-10
        assert abs(char_ngram_jaccard(a, b) - char_ngram_jaccard(b, a)) < 1e-10

    @given(a=st.text(min_size=0, max_size=2), b=st_short_text)
    @settings(max_examples=50)
    def test_empty_short_text_returns_zero(self, a, b):
        assert smart_similarity(a, b) == 0.0
        assert smart_similarity(b, a) == 0.0


# ═══════════════════════════════════════════════════════════════
#  rag/scoring.py — scoring invariants
# ═══════════════════════════════════════════════════════════════

from rag.scoring import CorpusStats, ScoredCandidate, Scorer, ScoringWeights


class TestScoringProperties:
    @given(
        rrf_score=st.floats(min_value=0.0, max_value=1.0),
        weight_rel=st.floats(min_value=0.0, max_value=2.0),
        weight_nov=st.floats(min_value=0.0, max_value=2.0),
        weight_tb=st.floats(min_value=0.0, max_value=2.0),
    )
    @settings(max_examples=200)
    def test_final_score_is_weighted_sum(self, rrf_score, weight_rel, weight_nov, weight_tb):
        scorer = Scorer(
            mode="rrf",
            weights=ScoringWeights(relevance=weight_rel, novelty=weight_nov, type_boost=weight_tb),
        )
        c = ScoredCandidate(id=1, page_id=1, title="t", content="c", wiki_type=None, rrf_score=rrf_score)
        result = scorer.rank_sync("q", [c], "user")
        r = result[0]
        expected = weight_rel * r.debug["relevance"] + weight_nov * r.debug["novelty"] + weight_tb * r.debug["type_boost"]
        assert abs(r.final_score - expected) < 1e-6

    @given(n=st.integers(min_value=1, max_value=30))
    @settings(max_examples=30)
    def test_ranking_ordering(self, n):
        scorer = Scorer(weights=ScoringWeights(relevance=1.0))
        candidates = [ScoredCandidate(id=i, page_id=i, title=f"t{i}", content=f"c{i}", wiki_type=None, rrf_score=float(i) / n) for i in range(n)]
        result = scorer.rank_sync("q", candidates, "u")
        scores = [c.final_score for c in result]
        assert scores == sorted(scores, reverse=True)

    @given(total=st.integers(min_value=0, max_value=200))
    @settings(max_examples=30)
    def test_corpus_stats_prior_range(self, total):
        stats = CorpusStats(
            total_retrievals=total,
            doc_retrieval_counts={i: i for i in range(min(total, 50))},
        )
        for doc_id in range(min(total, 50)):
            p = stats.prior(doc_id)
            assert 0.0 <= p <= 1.0

    @given(
        relevance=st.floats(min_value=-1.0, max_value=3.0),
        novelty=st.floats(min_value=-1.0, max_value=3.0),
        type_boost=st.floats(min_value=-1.0, max_value=3.0),
    )
    @settings(max_examples=100)
    def test_update_weights_clamped(self, relevance, novelty, type_boost):
        scorer = Scorer()
        scorer.update_weights({"relevance": relevance, "novelty": novelty, "type_boost": type_boost})
        assert 0.0 <= scorer.weights.relevance <= 2.0
        assert 0.0 <= scorer.weights.novelty <= 2.0
        assert 0.0 <= scorer.weights.type_boost <= 2.0


# ═══════════════════════════════════════════════════════════════
#  rag/quantize.py — binary encoding invariants
# ═══════════════════════════════════════════════════════════════

try:
    import numpy as np
    from rag.quantize import embed_to_binary, hamming_distance, hamming_to_score, _packed_bytes

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

pytestmark = pytest.mark.skipif(not HAS_NUMPY, reason="numpy not installed")


class TestQuantizeProperties:
    @given(emb=st_dim_vec)
    @settings(max_examples=100)
    def test_output_length(self, emb):
        result = embed_to_binary(emb, dim=DIM)
        assert len(result) == _packed_bytes(DIM)

    @given(emb=st_dim_vec, threshold=st.floats(min_value=-5.0, max_value=5.0))
    @settings(max_examples=100)
    def test_output_length_with_threshold(self, emb, threshold):
        result = embed_to_binary(emb, threshold=threshold, dim=DIM)
        assert len(result) == _packed_bytes(DIM)

    @given(emb=st.lists(st.floats(min_value=0.5, max_value=10.0, allow_nan=False, allow_infinity=False), min_size=DIM, max_size=DIM))
    @settings(max_examples=100)
    def test_all_positive_embedding(self, emb):
        result = embed_to_binary(emb, threshold=0.0, dim=DIM)
        arr = np.frombuffer(result, dtype=np.uint8)
        bits = np.unpackbits(arr, bitorder="big")[:DIM]
        assert bits.mean() > 0.8

    @given(emb=st_dim_vec)
    @settings(max_examples=100)
    def test_hamming_distance_self_zero(self, emb):
        b = embed_to_binary(emb, dim=DIM)
        assert hamming_distance(b, b) == 0

    @given(a=st_dim_vec, b=st_dim_vec)
    @settings(max_examples=100)
    def test_hamming_distance_symmetric(self, a, b):
        ba = embed_to_binary(a, dim=DIM)
        bb = embed_to_binary(b, dim=DIM)
        assert hamming_distance(ba, bb) == hamming_distance(bb, ba)

    @given(distance=st.integers(min_value=0, max_value=DIM))
    @settings(max_examples=50)
    def test_hamming_to_score_range(self, distance):
        score = hamming_to_score(distance, dim=DIM)
        assert 0.0 <= score <= 1.0

    @given(distance=st.integers(min_value=0, max_value=DIM - 1))
    @settings(max_examples=50)
    def test_hamming_to_score_monotonic(self, distance):
        assert hamming_to_score(distance, dim=DIM) > hamming_to_score(distance + 1, dim=DIM)


# ═══════════════════════════════════════════════════════════════
#  features/secrets.py — encrypt/decrypt roundtrip
# ═══════════════════════════════════════════════════════════════

from features.secrets import encrypt_json, decrypt_json


class TestSecretsProperties:
    @given(data=st.dictionaries(st.text(min_size=1, max_size=20), st.text(max_size=100), min_size=1, max_size=5))
    @settings(deadline=None, max_examples=30)
    def test_encrypt_decrypt_roundtrip_dict(self, data):
        blob = encrypt_json(data)
        result = decrypt_json(blob)
        assert result == data

    @given(data=st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=5))
    @settings(deadline=None, max_examples=30)
    def test_encrypt_decrypt_roundtrip_list(self, data):
        blob = encrypt_json(data)
        result = decrypt_json(blob)
        assert result == data

    @given(
        a=st.dictionaries(st.text(min_size=1, max_size=10), st.text(max_size=50), min_size=1),
        b=st.dictionaries(st.text(min_size=1, max_size=10), st.text(max_size=50), min_size=1),
    )
    @settings(deadline=None, max_examples=30)
    def test_different_inputs_different_ciphertext(self, a, b):
        assume(a != b)
        blob_a = encrypt_json(a)
        blob_b = encrypt_json(b)
        assert blob_a != blob_b

    @given(data=st.dictionaries(st.text(min_size=1, max_size=10), st.integers(), min_size=1))
    @settings(deadline=None, max_examples=20)
    def test_min_blob_size(self, data):
        """Encrypted blob must be at least nonce(24) + MAC(16) = 40 bytes."""
        blob = encrypt_json(data)
        assert len(blob) >= 40


# ═══════════════════════════════════════════════════════════════
#  core/reflex.py — ring buffer invariants
# ═══════════════════════════════════════════════════════════════

from core.reflex import ReflexBuffer


class TestReflexBufferProperties:
    """Properties that ring buffer must satisfy under any sequence of operations."""

    @given(n=st.integers(min_value=1, max_value=200))
    @settings(max_examples=100)
    def test_size_never_exceeds_max(self, n):
        """After adding n entries to buffer of size 10, size ≤ 10."""
        buf = ReflexBuffer(max_size=10)
        for i in range(n):
            buf.add(role="user", content=f"msg{i}", tokens=1)
        assert buf.size() <= 10

    @given(entries=st.lists(st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=("Cs",))), min_size=1, max_size=100))
    @settings(max_examples=50)
    def test_get_recent_returns_last_n(self, entries):
        """get_recent(k) returns last min(k, size) entries in order."""
        buf = ReflexBuffer(max_size=50)
        for e in entries:
            buf.add(role="user", content=e, tokens=1)
        recent = buf.get_recent(10)
        full = buf.get_full()
        expected = full[-10:]
        assert [e.content for e in recent] == [e.content for e in expected]

    @given(n=st.integers(min_value=1, max_value=50))
    @settings(max_examples=50)
    def test_fifo_eviction_order(self, n):
        """Older entries are evicted first when buffer is full."""
        buf = ReflexBuffer(max_size=5)
        for i in range(n):
            buf.add(role="user", content=f"msg{i}", tokens=1)
        full = buf.get_full()
        contents = [e.content for e in full]
        # All present entries should be in insertion order
        assert contents == sorted(contents, key=lambda x: int(x.replace("msg", "")))

    @given(n=st.integers(min_value=1, max_value=50))
    @settings(max_examples=30)
    def test_clear_resets_size(self, n):
        """After clear(), size is 0."""
        buf = ReflexBuffer(max_size=10)
        for i in range(n):
            buf.add(role="user", content=f"msg{i}", tokens=1)
        buf.clear()
        assert buf.size() == 0
        assert buf.get_full() == []


class TestReflexBufferConcurrency:
    """Ring buffer must handle concurrent add/get without crashes."""

    def test_concurrent_add_no_crash(self):
        """10 threads adding 100 entries each to buffer of size 50."""
        buf = ReflexBuffer(max_size=50)
        errors = []

        def adder(thread_id):
            try:
                for i in range(100):
                    buf.add(role="user", content=f"t{thread_id}_m{i}", tokens=1)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=adder, args=(t,)) for t in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Concurrent add failed: {errors}"
        assert buf.size() <= 50

    def test_concurrent_read_write_no_crash(self):
        """Reads and writes happening simultaneously."""
        buf = ReflexBuffer(max_size=30)
        errors = []

        def writer():
            try:
                for i in range(200):
                    buf.add(role="user", content=f"msg{i}", tokens=1)
                    time.sleep(0.0001)
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for _ in range(200):
                    buf.get_recent(5)
                    buf.get_full()
                    time.sleep(0.0001)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer), threading.Thread(target=reader)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Concurrent read/write failed: {errors}"


# ═══════════════════════════════════════════════════════════════
#  shared/middleware.py — ImportanceGate threshold invariant
# ═══════════════════════════════════════════════════════════════

import asyncio
import tempfile
from shared.middleware import MiddlewareContext, ImportanceGateMiddleware


class TestImportanceGateProperties:
    """ImportanceGate must correctly block/allow based on content scoring."""

    @given(value=st.text(min_size=0, max_size=500))
    @settings(max_examples=100)
    def test_gate_always_returns_bool(self, value):
        """Gate must never crash — always returns a result."""
        gate = ImportanceGateMiddleware()
        ctx = MiddlewareContext(args={"value": value}, tool_name="memory_user_remember")

        async def handler(c):
            return {"ok": True}

        result = asyncio.run(gate.process(ctx, handler))
        assert result is not None
        assert isinstance(ctx.blocked, bool)

    @given(score=st.floats(min_value=0.0, max_value=1.0))
    @settings(max_examples=50)
    def test_non_matching_tool_passes(self, score):
        """Non-memory tools should always pass through."""
        gate = ImportanceGateMiddleware()
        ctx = MiddlewareContext(args={"importance": score}, tool_name="other_tool")

        async def handler(c):
            return {"ok": True}

        asyncio.run(gate.process(ctx, handler))
        assert ctx.blocked is False


# ═══════════════════════════════════════════════════════════════
#  shared/memory_types.py — decay and archive invariants
# ═══════════════════════════════════════════════════════════════

from shared.memory_types import apply_decay, can_archive, kind_for_text, MemoryKind


class TestMemoryTypeProperties:
    """Memory type policies must hold for all inputs."""

    @given(days=st.integers(min_value=0, max_value=36500))
    @settings(max_examples=50)
    def test_instruction_never_decays(self, days):
        """Instruction importance stays constant regardless of age."""
        assert apply_decay(0.7, "instruction", days) == 0.7
        assert apply_decay(1.0, "instruction", days) == 1.0

    @given(days=st.integers(min_value=1, max_value=3650))
    @settings(max_examples=50)
    def test_fact_always_decays(self, days):
        """Fact importance decreases over time."""
        fresh = apply_decay(0.5, "fact", 1)
        aged = apply_decay(0.5, "fact", days)
        if days > 1:
            assert aged <= fresh

    @given(kind=st.sampled_from(["instruction", "rule", "commitment"]))
    @settings(max_examples=30)
    def test_protected_kinds_never_archive(self, kind):
        """Protected kinds cannot be archived regardless of age/importance."""
        assert can_archive(kind, 0.01, days_since_update=99999) is False

    @given(text=st.text(min_size=3, max_size=200, alphabet=st.characters(blacklist_categories=("Cs",))))
    @settings(max_examples=100)
    def test_kind_for_text_returns_valid(self, text):
        """kind_for_text always returns a valid MemoryKind."""
        result = kind_for_text(text)
        assert isinstance(result, MemoryKind)


# ═══════════════════════════════════════════════════════════════
#  shared/path_safety.py — path traversal invariant
# ═══════════════════════════════════════════════════════════════

from pathlib import Path


class TestPathSafetyProperties:
    """safe_resolve must never escape the base directory."""

    @given(target=st.text(min_size=0, max_size=50, alphabet=st.characters(blacklist_categories=("Cs",))))
    @settings(max_examples=100)
    def test_resolve_stays_within_base(self, target):
        """Resolved path must always start with base."""
        from shared.path_safety import safe_resolve

        tmp = Path(tempfile.mkdtemp())
        try:
            result = safe_resolve(tmp, target)
            assert str(result).startswith(str(tmp))
        except (ValueError, OSError):
            pass  # Rejection is also correct


# ═══════════════════════════════════════════════════════════════
#  features/secrets.py — encrypt/decrypt roundtrip
# ═══════════════════════════════════════════════════════════════

from features.secrets import encrypt_json, decrypt_json


class TestSecretsProperties:
    @given(data=st.dictionaries(st.text(min_size=1, max_size=20), st.text(max_size=100), min_size=1, max_size=5))
    @settings(deadline=None, max_examples=30)
    def test_encrypt_decrypt_roundtrip_dict(self, data):
        blob = encrypt_json(data)
        result = decrypt_json(blob)
        assert result == data

    @given(data=st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=5))
    @settings(deadline=None, max_examples=30)
    def test_encrypt_decrypt_roundtrip_list(self, data):
        blob = encrypt_json(data)
        result = decrypt_json(blob)
        assert result == data

    @given(
        a=st.dictionaries(st.text(min_size=1, max_size=10), st.text(max_size=50), min_size=1),
        b=st.dictionaries(st.text(min_size=1, max_size=10), st.text(max_size=50), min_size=1),
    )
    @settings(deadline=None, max_examples=30)
    def test_different_inputs_different_ciphertext(self, a, b):
        assume(a != b)
        blob_a = encrypt_json(a)
        blob_b = encrypt_json(b)
        assert blob_a != blob_b

    @given(data=st.dictionaries(st.text(min_size=1, max_size=10), st.integers(), min_size=1))
    @settings(deadline=None, max_examples=20)
    def test_min_blob_size(self, data):
        """Encrypted blob must be at least nonce(24) + MAC(16) = 40 bytes."""
        blob = encrypt_json(data)
        assert len(blob) >= 40


# ═══════════════════════════════════════════════════════════════
#  shared/saga.py — Saga state machine invariants
# ═══════════════════════════════════════════════════════════════

from shared.saga import Saga


class TestSagaProperties:
    @given(name=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=("Cs",))))
    @settings(max_examples=50)
    def test_saga_name_preserved(self, name):
        """Saga name is preserved in state."""
        s = Saga(name)
        assert s.get_state()["name"] == name

    @given(n=st.integers(min_value=0, max_value=20))
    @settings(max_examples=30)
    def test_add_steps_count(self, n):
        """Adding n steps results in n steps."""
        s = Saga("test")
        for i in range(n):
            s.add_step(f"s{i}", lambda d: {"ok": True})
        assert len(s._steps) == n


# ═══════════════════════════════════════════════════════════════
#  shared/embeddings.py — hash embedding invariants
# ═══════════════════════════════════════════════════════════════

from shared.embeddings import _hash_embedding, similarity


class TestEmbeddingProperties:
    @given(
        text=st.text(min_size=1, max_size=200, alphabet=st.characters(blacklist_categories=("Cs",))),
        dim=st.integers(min_value=16, max_value=256),
    )
    @settings(max_examples=50)
    def test_hash_embedding_correct_dim(self, text, dim):
        """Hash embedding always returns correct dimension."""
        result = _hash_embedding(text, dim=dim)
        assert len(result) == dim

    @given(text=st.text(min_size=1, max_size=200, alphabet=st.characters(blacklist_categories=("Cs",))))
    @settings(max_examples=50)
    def test_hash_embedding_normalized(self, text):
        """Hash embedding is always normalized (unit vector)."""
        result = _hash_embedding(text, dim=64)
        norm = sum(x**2 for x in result) ** 0.5
        assert abs(norm - 1.0) < 0.01

    @given(text=st.text(min_size=1, max_size=200, alphabet=st.characters(blacklist_categories=("Cs",))))
    @settings(max_examples=50)
    def test_hash_embedding_deterministic(self, text):
        """Same input always produces same embedding."""
        r1 = _hash_embedding(text, dim=32)
        r2 = _hash_embedding(text, dim=32)
        assert r1 == r2

    @given(
        v=st.lists(st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False), min_size=2, max_size=20),
    )
    @settings(max_examples=50)
    def test_similarity_self_is_one(self, v):
        """Similarity of a non-zero vector with itself is ~1.0."""
        assume(any(abs(x) > 0.01 for x in v))  # skip near-zero vectors
        s = similarity(v, v)
        assert abs(s - 1.0) < 0.05

    @given(
        v1=st.lists(st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False), min_size=2, max_size=20),
        v2=st.lists(st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False), min_size=2, max_size=20),
    )
    @settings(max_examples=50)
    def test_similarity_symmetric(self, v1, v2):
        """Similarity is symmetric."""
        s1 = similarity(v1, v2)
        s2 = similarity(v2, v1)
        assert abs(s1 - s2) < 1e-10


# ═══════════════════════════════════════════════════════════════
#  shared/connection.py — database operation invariants
# ═══════════════════════════════════════════════════════════════

import uuid
from shared.connection import AsyncConnectionManager


class TestConnectionProperties:
    @given(n=st.integers(min_value=1, max_value=20))
    @settings(max_examples=20)
    def test_insert_fetchall_roundtrip(self, n):
        """Insert n rows, fetchall returns exactly n rows."""

        async def t():
            cm = AsyncConnectionManager(base_dir="/tmp")
            name = f"prop_{uuid.uuid4().hex[:8]}.db"
            conn = await cm.get(name)
            await conn.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER)")
            await conn.executemany("INSERT INTO t VALUES (?)", [(i,) for i in range(n)])
            await conn.commit()
            cur = await conn.execute("SELECT COUNT(*) FROM t")
            row = await cur.fetchone()
            return row[0]

        result = asyncio.run(t())
        assert result == n

    def test_get_reuses_connection(self):
        """Getting the same DB name returns the same connection object."""

        async def t():
            cm = AsyncConnectionManager(base_dir="/tmp")
            c1 = await cm.get("reuse_test.db")
            c2 = await cm.get("reuse_test.db")
            return c1 is c2

        result = asyncio.run(t())
        assert result is True

    def test_execute_script_works(self):
        """execute_script runs DDL and DML."""

        async def t():
            cm = AsyncConnectionManager(base_dir="/tmp")
            name = f"script_{uuid.uuid4().hex[:8]}.db"
            await cm.execute_script(name, "CREATE TABLE t (x INTEGER); INSERT INTO t VALUES (42);")
            conn = await cm.get(name)
            cur = await conn.execute("SELECT x FROM t")
            row = await cur.fetchone()
            return row[0]

        result = asyncio.run(t())
        assert result == 42


# ═══════════════════════════════════════════════════════════════
#  shared/cache.py — cache get/set invariant
# ═══════════════════════════════════════════════════════════════

from shared.cache import MemoryCache


class TestCacheProperties:
    @given(
        key=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=("Cs",))),
        value=st.text(min_size=1, max_size=200, alphabet=st.characters(blacklist_categories=("Cs",))),
    )
    @settings(max_examples=100)
    def test_set_get_roundtrip(self, key, value):
        """set(k, v) → get(k) returns v."""
        cache = MemoryCache()
        cache.set(key, value)
        assert cache.get(key) == value

    @given(key=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=("Cs",))))
    @settings(max_examples=50)
    def test_get_missing_returns_none(self, key):
        """get(k) for missing key returns None."""
        cache = MemoryCache()
        assert cache.get(key) is None

    @given(n=st.integers(min_value=1, max_value=20))
    @settings(max_examples=20)
    def test_size_after_inserts(self, n):
        """After inserting n unique keys, size == n."""
        cache = MemoryCache()
        for i in range(n):
            cache.set(f"k{i}", f"v{i}")
        assert cache.size() == n
