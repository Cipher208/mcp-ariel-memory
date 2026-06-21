# Тестирование и структура проекта

## Тестирование

```bash
# Все тесты (49 tests)
python -m pytest tests/ -v

# Только модульные
python -m pytest tests/test_core/ tests/test_rag/ -v

# MCP Inspector
uv run mcp dev mcp_server.py
```

**Статус:** 49/49 pytest + 36/36 integration + 33/33 MCP tools.

## Структура тестов

```
tests/
├── test_all.py              # 10 legacy tests
├── test_core/               # 6 tests
├── test_rag/                # 5 tests
├── test_graph/              # 4 tests
├── test_lifecycle/          # 3 tests
├── test_hooks/              # 3 tests
├── test_wiki/               # 3 tests
├── test_features/           # 6 tests
├── test_shared/             # 6 tests
└── test_mcp/                # 3 tests
```

## Структура проекта

```
mcp-ariel-memory/
├── pyproject.toml
├── Dockerfile / docker-compose.yml
├── openapi.yaml             # OpenAPI 3.1 spec
├── .github/workflows/ci.yml
├── config.yaml / config.py
├── mcp_server.py            # MCP SDK (33 async tools)
├── server.py                # Legacy (обратная совместимость)
├── docs/                    # Документация (13 файлов)
├── tests/                   # 49 pytest tests (модульные)
├── core/                    # L1-L4
├── rag/                     # FTS5 + RRF + fallback
├── graph/                   # Epistemic + Temporal
├── lifecycle/               # Forgetting + Emotion + Consolidation
├── hooks/                   # 24 hooks
├── wiki/                    # FileWiki (.md + FTS5)
├── features/                # Auth + Backup + Dashboard + Audit + RateLimit
└── shared/                  # Cache + Saga + Middleware + Embeddings + Metrics + Migrations + Replica
```
