# mcp-ariel-memory

**Universal Two-Layer Memory MCP Server**

[![CI](https://github.com/Cipher208/mcp-ariel-memory/actions/workflows/ci.yml/badge.svg)](https://github.com/Cipher208/mcp-ariel-memory/actions/workflows/ci.yml)

Two-layer universal memory for AI agents. Real MCP Python SDK, async, **37 tools**, stdio + Streamable HTTP, dashboard with auth + rate limiting, metrics, auto-backups with jitter, wiki with external folders, read-only replica.

[English](README_EN.md) | Русский

---

## Установка

### Вариант 1: npm (рекомендуется для MCP-клиентов)

```bash
npx mcp-ariel-memory --transport stdio
```

Требуется Python 3.10+ на машине. npm-обёртка автоматически ставит Python-пакет.

### Вариант 2: pip

```bash
pip install git+https://github.com/Cipher208/mcp-ariel-memory.git
python -m mcp_server --transport stdio
```

### Вариант 3: Docker

```bash
docker build -t ariel-memory .
docker run -p 8000:8000 ariel-memory
```

### Вариант 4: Из исходников

```bash
git clone https://github.com/Cipher208/mcp-ariel-memory.git
cd mcp-ariel-memory
pip install -e ".[all]"
python -m mcp_server --transport stdio
```

---

## Быстрый старт

### Claude Desktop

Добавить в `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ariel-memory": {
      "command": "npx",
      "args": ["mcp-ariel-memory", "--transport", "stdio"]
    }
  }
}
```

### HTTP сервер

```bash
python -m mcp_server --transport http --port 8000
```

---

## Документация

| # | Документ | Описание |
|---|----------|----------|
| 01 | [Архитектура](docs/01-architecture.md) | Стек, двухслойная модель, L1-L4, консолидация |
| 02 | [MCP Tools](docs/02-mcp-tools.md) | Все 37 tools с параметрами и примерами |
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

- **MCP Tools:** 37
- **pytest:** 104 passed
- **Python файлов:** 70
- **Таблиц БД:** 21
- **Хуки:** 24
- **Wiki типов:** 14
- **Миграции БД:** 3

---

## Лицензия

MIT License — см. [LICENSE](LICENSE).
