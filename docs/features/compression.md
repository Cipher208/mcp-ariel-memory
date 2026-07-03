# Compression

## Features

- Automatic compression of old memories
- Configurable compression thresholds
- Preserves important memories
- Reduces storage usage

## Usage

```python
from features.compression import compress_memories

# Compress memories older than 30 days with importance < 0.3
compressed = await compress_memories(user_id="u1", days=30, threshold=0.3)
```
