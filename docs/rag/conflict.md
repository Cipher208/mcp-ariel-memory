# Conflict Resolution

Detects conflicting memory entries using BM25 + char-trigram similarity.

## Similarity Functions

### bm25_pair_similarity

BM25 between two documents (pseudo-corpus of 2). Returns [0, 1].

### char_ngram_jaccard

Char-trigram Jaccard similarity. Returns [0, 1].

### smart_similarity

Adaptive: short → ngram only, medium → weighted, long → BM25-heavy.

## Properties (Hypothesis-verified)

- All similarity functions return [0, 1]
- Symmetric: `sim(a, b) == sim(b, a)`
- Empty/short text returns 0
- Self-similarity ≥ 0

## Usage

```python
from rag.conflict import smart_similarity

score = smart_similarity("PostgreSQL is fast", "MySQL is fast")  # ~0.6
score = smart_similarity("hello", "completely different")  # ~0.0
```
