# Quantization

Binary embedding (MIB) for fast similarity search.

## Usage

```python
from rag.quantize import embed_to_binary, hamming_distance, hamming_to_score

# Binarize
binary = embed_to_binary(embedding, threshold=0.0, dim=384)

# Distance
dist = hamming_distance(binary_a, binary_b)

# Score
score = hamming_to_score(dist, dim=384)  # ∈ [0, 1]
```

## Properties (Hypothesis-verified)

- Output length = `ceil(dim / 8)`
- `hamming_distance(a, a) == 0`
- `hamming_distance(a, b) == hamming_distance(b, a)`
- `hamming_to_score` is monotonically decreasing
