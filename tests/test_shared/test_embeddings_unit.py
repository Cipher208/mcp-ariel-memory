"""Tests for shared/embeddings.py — hash embedding, similarity, cache."""

import pytest
from shared.embeddings import _hash_embedding, similarity


def test_hash_embedding_dim():
    result = _hash_embedding("test text", dim=128)
    assert len(result) == 128


def test_hash_embedding_normalized():
    result = _hash_embedding("test", dim=64)
    norm = sum(x**2 for x in result) ** 0.5
    assert abs(norm - 1.0) < 0.01


def test_hash_embedding_deterministic():
    r1 = _hash_embedding("hello", dim=32)
    r2 = _hash_embedding("hello", dim=32)
    assert r1 == r2


def test_hash_embedding_different_inputs():
    r1 = _hash_embedding("hello", dim=32)
    r2 = _hash_embedding("world", dim=32)
    assert r1 != r2


def test_similarity_identical():
    v = [1.0, 0.0, 0.0]
    assert similarity(v, v) == pytest.approx(1.0)


def test_similarity_orthogonal():
    v1 = [1.0, 0.0, 0.0]
    v2 = [0.0, 1.0, 0.0]
    assert similarity(v1, v2) == pytest.approx(0.0)


def test_similarity_zero_vector():
    v1 = [1.0, 0.0]
    v2 = [0.0, 0.0]
    assert similarity(v1, v2) == 0.0


def test_similarity_opposite():
    v1 = [1.0, 0.0]
    v2 = [-1.0, 0.0]
    assert similarity(v1, v2) == pytest.approx(-1.0)
