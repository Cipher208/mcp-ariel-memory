# Testing and Project Structure

## Testing

```bash
# All tests (246 tests)
python -m pytest tests/ -v

# Single test file
python -m pytest tests/test_auth_crypto.py -v

# MCP Inspector
uv run mcp dev mcp_server.server
```

**Status:** 246/246 pytest + 19/19 MCP tools. Python 3.10–3.13 CI matrix. Single `memory.db` file. Envelope encryption for sensitive data.

## Test Fixtures

Shared `master_key_env` fixture in `tests/conftest.py` sets `MCP_MASTER_KEY` for all tests. Individual test files should NOT define their own `master_key_env`.

## Performance Optimizations

| Optimization | Description | Impact |
|-------------|-------------|--------|
| `memory_context_inject` caching | 30s TTL cache | 4 DB queries → 0 on cache hit |
| `memory_recall` caching | 10s TTL cache | Reduces repeated DB queries |
| `memory_stats` optimization | `COUNT(*)` instead of `get_episodes(1000)` | Faster statistics |
| `memory_remember` (agent) parallelization | `asyncio.gather` for core + graph writes | +14% throughput |

## Benchmark Results

| Operation | Before | After | Change |
|-----------|--------|-------|--------|
| `memory_remember` | 1344 ops/s | 1533 ops/s | +14% |
| `encrypt+decrypt` | 382 ops/s | 402 ops/s | +5% |

## Tests — async

All tests use `asyncio.run()` to call async methods:

```python
def test_user_remember():
    from core import memory_manager
    async def t():
        await memory_manager.user_memory("alice").remember("name", "Alice")
        results = await memory_manager.user_memory("alice").recall("name")
        assert len(results) > 0
    asyncio.run(t())
```

## Project Structure

```
mcp-ariel-memory/
├── pyproject.toml
├── Dockerfile / docker-compose.yml
├── openapi.yaml
├── .github/workflows/ci.yml
├── config.yaml / config.py
├── mcp_server/                 # MCP SDK (19 unified tools)
│   ├── __init__.py
│   ├── server.py              # FastMCP, AppContext, lifespan, main()
│   ├── tools_layer.py         # Unified layer tools (user/agent)
│   ├── tools_ops.py           # Ops tools (auth, backup, saga, data)
│   ├── models.py              # Pydantic return type models
│   └── schema.py              # OpenAPI/JSON schema generator
├── rag/                        # RAG module with unified search
│   ├── engine.py              # search() facade + strategies
│   ├── scoring.py             # Scorer, ScoringWeights, ScoredCandidate
│   ├── quantize.py            # MIB binarization + supervised thresholds
│   └── ...
├── docs/                      # 13 documents
├── tests/                     # 246 pytest tests
│   ├── conftest.py            # Shared fixtures (master_key_env)
│   ├── test_all.py            # Core integration tests
│   ├── test_auth_backup.py    # Auth + backup + config tests
│   ├── test_auth_crypto.py    # Encryption + rotation tests
│   ├── test_tools_layer.py    # Unified layer tool tests
│   ├── test_tools_ops.py      # Ops tool tests
│   ├── test_rag_scoring.py    # Scorer unit tests
│   ├── test_rag_search_facade.py  # Unified search tests
│   ├── test_threshold_training.py  # Supervised threshold tests
│   └── ...
├── core/                      # L1-L4 (async via AsyncConnectionManager)
├── graph/                     # Epistemic + Temporal (async)
├── lifecycle/                 # Forgetting + Emotion + Consolidation (async)
├── hooks/                     # 24 hooks
├── wiki/                      # FileWiki (.md + FTS5, async)
├── features/                  # Auth + Backup + Dashboard + Audit + RateLimit + Secrets (async)
└── shared/                    # ConnectionManager + Cache + Saga + Middleware + Embeddings (async)
```
