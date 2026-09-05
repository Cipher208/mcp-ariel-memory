"""Weighted Hamming (draft v37 §EDM, опция): информационные веса битов."""

import pytest

from rag.quantize import binary_from_threshold_array, bit_frequency_weights, weighted_hamming_score


def _bin_from(emb: list[float]) -> bytes:
    return binary_from_threshold_array(emb, [0.0] * len(emb))


def test_bit_frequency_weights_rare_bit_heavier():
    """Бит, выставленный редко, весит больше константного (MSB-first: 0x01 = бит 7)."""
    corpus = [bytes([0b1000_0000]) for _ in range(99)] + [bytes([0b1100_0000])]  # бит 0 константный, бит 1 редкий
    w = bit_frequency_weights(corpus, dim=8)
    assert w[1] > w[0]  # бит 1 (P≈0.01) против бита 0 (P≈0.99, clamped floor)
    assert w[0] == pytest.approx(0.1), "floor 0.1 для константного бита"
    assert len(w) == 8


def test_bit_frequency_weights_empty_corpus_uniform():
    assert bit_frequency_weights([], dim=4) == [1.0, 1.0, 1.0, 1.0]


def test_weighted_hamming_self_similarity_is_one():
    b = _bin_from([0.5, -0.5, 0.5, -0.5] * 2)
    w = [1.0] * 8
    assert weighted_hamming_score(b, b, w, dim=8) == pytest.approx(1.0)


def test_weighted_hamming_orders_by_informative_diff():
    """Равное число различившихся битов: различие в тяжёлом бите хуже, чем в лёгком."""
    a = bytes([0b0000_0000])
    diff_heavy = bytes([0b1000_0000])  # различие в бите 0 (вес 5.0)
    diff_light = bytes([0b0100_0000])  # различие в бите 1 (вес 0.1)
    weights = [5.0, 0.1, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    assert weighted_hamming_score(a, diff_light, weights, dim=8) > weighted_hamming_score(a, diff_heavy, weights, dim=8)


def test_weighted_hamming_wrong_weights_dim_raises():
    with pytest.raises(ValueError):
        weighted_hamming_score(b"\x00", b"\x00", [1.0] * 3, dim=8)
