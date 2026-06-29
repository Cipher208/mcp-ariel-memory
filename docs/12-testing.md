# Testing and Project Structure

## Testing

```bash
# All tests (158 tests)
python -m pytest tests/ -v

# Single test file
python -m pytest tests/test_auth_crypto.py -v

# MCP Inspector
uv run mcp dev mcp_server.py
```

**Status:** 158/158 pytest + 37/37 MCP tools. Python 3.10–3.13 CI matrix. Single `memory.db` file. Envelope encryption for sensitive data.

## Test Fixtures

Shared `master_key_env` fixture in `tests/conftest.py` sets `MCP_MASTER_KEY` for all tests. Individual test files should NOT define their own `master_key_env`.

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
├── tests/                     # 158 pytest tests
│   ├── conftest.py            # Shared fixtures (master_key_env)
│   ├── test_all.py            # Core integration tests
│   ├── test_auth_backup.py    # Auth + backup + config tests
│   ├── test_auth_crypto.py    # Encryption + rotation tests
│   └── ...
├── core/                      # L1-L4 (async via AsyncConnectionManager)
├── rag/                       # FTS5 + RRF (async)
├── graph/                     # Epistemic + Temporal (async)
├── lifecycle/                 # Forgetting + Emotion + Consolidation (async)
├── hooks/                     # 24 hooks
├── wiki/                      # FileWiki (.md + FTS5, async)
├── features/                  # Auth + Backup + Dashboard + Audit + RateLimit + Secrets (async)
└── shared/                    # ConnectionManager + Cache + Saga + Middleware + Embeddings (async)
```
