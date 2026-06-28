"""Tests for _chunk_text with overlap."""

import pytest
from rag.engine import RAGEngine


@pytest.fixture
def rag():
    return RAGEngine(binary_dim=8)  # no DB needed


def test_overlap_param_now_used(rag):
    text = "Paragraph one is here.\n\n" * 30
    chunks = rag._chunk_text(text, max_size=200, overlap=50)
    assert all(len(c) <= 230 for c in chunks)  # max + 1 paragraph overlap
    # Overlap between adjacent chunks > 0
    overlaps = sum(1 for a, b in zip(chunks, chunks[1:]) if any(line in b for line in a.split("\n\n") if line))
    assert overlaps >= len(chunks) - 1


def test_overlap_validation(rag):
    with pytest.raises(ValueError):
        rag._chunk_text("x", max_size=100, overlap=100)


def test_long_paragraph_word_split(rag):
    long_para = " ".join(["word"] * 300)
    chunks = rag._chunk_text(long_para, max_size=100, overlap=20)
    assert all(len(c) <= 120 for c in chunks)
    # With overlap, word count may exceed 300 due to duplicated words at boundaries
    assert sum(len(c.split()) for c in chunks) >= 300
