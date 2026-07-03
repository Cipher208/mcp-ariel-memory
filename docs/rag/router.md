# Router

Routes queries to appropriate search strategy.

## Auto Strategy

- Short queries (1-2 words) → FTS
- Long queries (3+ words) → Hybrid

## Usage

```python
from rag.router import route_query

strategy = route_query("redis")
# strategy = "fts"

strategy = route_query("how to configure database replication")
# strategy = "hybrid"
```
