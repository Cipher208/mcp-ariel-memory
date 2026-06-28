# Testing and Project Structure

## Testing

```bash
# All tests (56 tests, async)
python -m pytest tests/ -v

# MCP Inspector
uv run mcp dev mcp_server.py
```

**Status:** 56/56 pytest + 37/37 MCP tools. Single `memory.db` file. Async in saga steps.

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
├── mcp_server.py              # MCP SDK (37 async tools)
├── server.py                  # Legacy sync wrapper
├── docs/                      # 13 documents
├── tests/                     # 56 async pytest tests
├── core/                      # L1-L4 (async via AsyncConnectionManager)
├── rag/                       # FTS5 + RRF (async)
├── graph/                     # Epistemic + Temporal (async)
├── lifecycle/                 # Forgetting + Emotion + Consolidation (async)
├── hooks/                     # 24 hooks
├── wiki/                      # FileWiki (.md + FTS5, async)
├── features/                  # Auth + Backup + Dashboard + Audit + RateLimit (async)
└── shared/                    # ConnectionManager + Cache + Saga + Middleware + Embeddings (async)
```
