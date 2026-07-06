"""Unit tests for rag/quantize — parametrized."""

import pytest

from rag.quantize import (
    binary_batch,
    embed_to_binary,
    hamming_distance,
    hamming_to_score,
    supervised_threshold,
)


@pytest.mark.parametrize("emb,threshold,expected_byte", [
    ([0.1, -0.2, 0.3, -0.4], 0.0, 0b10100000),
    ([0.1, -0.2, 0.3, -0.4], 0.5, 0x00),
])
def test_embed_to_binary(emb, threshold, expected_byte):
    packed = embed_to_binary(emb, threshold=threshold, dim=4)
    if expected_byte == 0x00:
        assert packed == b"\x00"
    else:
        assert packed[0] == expected_byte


@pytest.mark.parametrize("a,b,expected", [
    (b"\xff" * 6, b"\xff" * 6, 0),
    (b"\xff" * 6, b"\x00" * 6, 48),
])
def test_hamming_distance(a, b, expected):
    assert hamming_distance(a, b) == expected


def test_hamming_to_score():
    assert hamming_to_score(0) == 1.0
    assert hamming_to_score(384, dim=384) == pytest.approx(0.0)


def test_binary_batch_consistent():
    embs = [
        [0.1, -0.2, 0.3, -0.4, 0.5, -0.6, 0.7, -0.8],
        [-0.1, 0.2, -0.3, 0.4, -0.5, 0.6, -0.7, 0.8],
    ]
    batched = binary_batch(embs, dim=8)
    single = [embed_to_binary(e, dim=8) for e in embs]
    assert batched == single


def test_supervised_threshold():
    import numpy as np

    pos_pairs = [([0.8, 0.2] * 192, [0.9, 0.3] * 192)]
    thr = supervised_threshold(pos_pairs, dim=384, n_candidates=10)
    assert thr.shape == (384,)
    assert np.isfinite(thr).all()


def test_binary_pipeline_roundtrip():
    import numpy as np

    rng = np.random.default_rng(42)
    a = rng.normal(0, 1, size=384).tolist()
    bin_a = embed_to_binary(a, dim=384)
    bin_b = embed_to_binary(a[:], dim=384)
    assert hamming_distance(bin_a, bin_b) == 0


@pytest.mark.parametrize("emb,dim,match", [
    ([0.1, -0.2, 0.3], 4, "expected dim=4"),
    (b"\xff" * 6, None, None),  # length mismatch tested separately
])
def test_edge_cases(emb, dim, match):
    if dim is not None:
        with pytest.raises(ValueError, match=match):
            embed_to_binary(emb, dim=dim)
    else:
        with pytest.raises(ValueError, match="length mismatch"):
            hamming_distance(emb, b"\xff" * 5)


def test_binary_batch_invalid_shape():
    embs = [[0.1, 0.2]]
    with pytest.raises(ValueError):
        binary_batch(embs, dim=8)
