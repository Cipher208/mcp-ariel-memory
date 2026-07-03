# Testing

## Running Tests

```bash
# Full suite
pytest tests/ -v --timeout=30

# Specific module
pytest tests/test_hypothesis.py -v

# With coverage
pytest tests/ --cov=features --cov=shared
```

## Test Categories

| Category | Count | Description |
|----------|-------|-------------|
| Unit | ~200 | Individual function tests |
| Integration | ~100 | Cross-module tests |
| Property-based | 25 | Hypothesis tests for invariants |

## Property-Based Tests

Hypothesis tests verify mathematical invariants:

- Similarity functions: range [0,1], symmetry
- Scoring: weighted sum, ordering
- Quantization: output length, hamming distance
- Secrets: encrypt/decrypt roundtrip
- Ring buffer: size invariant, FIFO, concurrency

## Benchmarks

```bash
# RAG search benchmarks
python -m pytest tests/test_rag*.py -v --benchmark-only
```
