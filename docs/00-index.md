# mcp-ariel-memory — Документация

**Universal Two-Layer Memory MCP Server**

[![CI](https://github.com/ariel-memory/mcp-ariel-memory/actions/workflows/ci.yml/badge.svg)](https://github.com/ariel-memory/mcp-ariel-memory/actions/workflows/ci.yml)

Двухслойная универсальная память для AI-агентов. Реальный MCP Python SDK, async, **33 tools**, stdio + Streamable HTTP транспорты, dashboard с auth + rate limiting, метрики, автобэкапи с jitter, внешние папки wiki, read-only replica, OpenAPI spec. **Нативный async через aiosqlite** — без `asyncio.to_thread()` прослойки.

---

## Оглавление

| # | Документ | Описание |
|---|----------|----------|
| 01 | [Архитектура](01-architecture.md) | Стек, двухслойная модель, L1-L4, консолидация |
| 02 | [MCP Tools](02-mcp-tools.md) | Все 33 tools с параметрами и примерами |
| 03 | [Ядро памяти](03-core.md) | ReflexBuffer, SessionStore, EpisodicMemory, CoreMemory |
| 04 | [Поиск (RAG)](04-rag.md) | FTS5 + fallback, RRF, RetrievalRouter, ConflictResolver |
| 05 | [Граф знаний](05-graph.md) | EpistemicGraph, TemporalGraph |
| 06 | [Жизненный цикл](06-lifecycle.md) | Forgetting, EmotionTrigger (RU+EN), Consolidation |
| 07 | [Хуки](07-hooks.md) | 24 хука (12 user + 12 agent) |
| 08 | [Wiki](08-wiki.md) | FileWiki (.md files + FTS5) |
| 09 | [Фичи](09-features.md) | Auth (persistent), Backup (jitter), Dashboard, Audit, RateLimit (HTTP + WS) |
| 10 | [Общие компоненты](10-shared.md) | Cache, Saga+Watchdog, Middleware, Embeddings (multilingual), Metrics, DreamBuffer, Archive, Migrations, Read-only replica |
| 11 | [Операции](11-operations.md) | Транспорты, Dashboard, Auth, Backup, Конфигурация, OpenAPI |
| 12 | [Тестирование](12-testing.md) | pytest, структура, статус |

---

## Быстрый старт

```bash
git clone <repo> && cd mcp-ariel-memory
pip install -e ".[all]"
python -m mcp_ariel_memory --transport stdio
```

### Docker

```bash
docker build -t ariel-memory .
docker run -v $(pwd)/config.yaml:/app/config.yaml:ro -p 8000:8000 ariel-memory
# Или docker-compose (автоматически монтирует config.yaml)
docker-compose up
```

### Claude Desktop

```json
{
  "mcpServers": {
    "ariel-memory": {
      "command": "python",
      "args": ["-m", "mcp_ariel_memory", "--transport", "stdio"],
      "cwd": "/path/to/mcp-ariel-memory"
    }
  }
}
```
