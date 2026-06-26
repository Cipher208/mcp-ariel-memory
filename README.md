# mcp-ariel-memory

**Universal Two-Layer Memory MCP Server**

[![CI](https://github.com/ariel-memory/mcp-ariel-memory/actions/workflows/ci.yml/badge.svg)](https://github.com/ariel-memory/mcp-ariel-memory/actions/workflows/ci.yml)

Двухслойная универсальная память для AI-агентов. Реальный MCP Python SDK, async, **33 tools**, stdio + Streamable HTTP, dashboard с auth + rate limiting, метрики, автобэкапи с jitter, wiki с внешними папками, read-only replica, OpenAPI spec.

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
docker run -p 8000:8000 ariel-memory
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

---

## Документация

| # | Документ | Описание |
|---|----------|----------|
| 01 | [Архитектура](docs/01-architecture.md) | Стек, двухслойная модель, L1-L4, консолидация |
| 02 | [MCP Tools](docs/02-mcp-tools.md) | Все 31 tool с параметрами и примерами |
| 03 | [Ядро памяти](docs/03-core.md) | ReflexBuffer, SessionStore, EpisodicMemory, CoreMemory |
| 04 | [Поиск (RAG)](docs/04-rag.md) | FTS5, RRF, RetrievalRouter, ConflictResolver |
| 05 | [Граф знаний](docs/05-graph.md) | EpistemicGraph, TemporalGraph |
| 06 | [Жизненный цикл](docs/06-lifecycle.md) | Forgetting, EmotionTrigger, Consolidation |
| 07 | [Хуки](docs/07-hooks.md) | 24 хука (12 user + 12 agent) |
| 08 | [Wiki](docs/08-wiki.md) | FileWiki (файлы как source of truth + FTS5) |
| 09 | [Фичи](docs/09-features.md) | Auth, Backup, Dashboard, Audit, RateLimit |
| 10 | [Общие компоненты](docs/10-shared.md) | Cache, Saga+Watchdog, Middleware, Embeddings, Metrics |
| 11 | [Операции](docs/11-operations.md) | Транспорты, Dashboard, Auth, Backup, Конфигурация |
| 12 | [Тестирование](docs/12-testing.md) | pytest, структура проекта |

---

## Статус

- **MCP Tools:** 33
- **pytest:** 56/56
- **Файлов .py:** 50+
- **Хуки:** 24
- **Wiki типов:** 14
- **Миграции БД:** 3
