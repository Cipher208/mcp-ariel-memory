# mcp-ariel-memory — Документация

**Universal Two-Layer Memory MCP Server**

[![CI](https://github.com/ariel-memory/mcp-ariel-memory/actions/workflows/ci.yml/badge.svg)](https://github.com/ariel-memory/mcp-ariel-memory/actions/workflows/ci.yml)

Двухслойная универсальная память для AI-агентов. Реальный MCP Python SDK, async, 31 tool, stdio + Streamable HTTP транспорты, dashboard, метрики, аутентификация, автобэкапы, внешние папки wiki.

---

## Оглавление

| # | Документ | Описание |
|---|----------|----------|
| 01 | [Архитектура](01-architecture.md) | Стек, двухслойная модель, L1-L4, консолидация |
| 02 | [MCP Tools](02-mcp-tools.md) | Все 31 tool с параметрами и примерами |
| 03 | [Ядро памяти](03-core.md) | core/ — ReflexBuffer, SessionStore, EpisodicMemory, CoreMemory |
| 04 | [Поиск (RAG)](04-rag.md) | rag/ — FTS5, RRF, RetrievalRouter, ConflictResolver |
| 05 | [Граф знаний](05-graph.md) | graph/ — EpistemicGraph, TemporalGraph |
| 06 | [Жизненный цикл](06-lifecycle.md) | lifecycle/ — Forgetting, EmotionTrigger, Consolidation |
| 07 | [Хуки](07-hooks.md) | hooks/ — 24 хука (12 user + 12 agent) |
| 08 | [Wiki](08-wiki.md) | wiki/ — FileWiki (файлы как source of truth + FTS5) |
| 09 | [Фичи](09-features.md) | features/ — Auth, Backup, Dashboard, Audit, RateLimit, ImportExport |
| 10 | [Общие компоненты](10-shared.md) | shared/ — Cache, Saga+Watchdog, Middleware, Embeddings, Metrics, DreamBuffer, Archive |
| 11 | [Операции](11-operations.md) | Транспорты, Dashboard, Auth, Backup Cron, Конфигурация |
| 12 | [Тестирование](12-testing.md) | pytest, структура проекта, статус |

---

## Быстрый старт

```bash
# Установка
git clone <repo> && cd mcp-ariel-memory
pip install -e ".[all]"

# Запуск (stdio — для Claude Desktop)
python -m mcp_ariel_memory --transport stdio

# Запуск (HTTP — для веб-клиентов)
python -m mcp_ariel_memory --transport http --port 8000

# Запуск (HTTP + Dashboard + Metrics)
python -m mcp_ariel_memory --transport http --port 8000 --dashboard
```

### Docker

```bash
docker build -t ariel-memory .
docker run -v $(pwd)/config.yaml:/app/config.yaml:ro -p 8000:8000 ariel-memory

# Или docker-compose (автоматически монтирует config.yaml)
docker-compose up
```

### Claude Desktop

Добавить в `claude_desktop_config.json`:

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

Windows:
```json
{
  "mcpServers": {
    "ariel-memory": {
      "command": "cmd",
      "args": ["/c", "python", "-m", "mcp_ariel_memory", "--transport", "stdio"],
      "cwd": "C:\\Users\\You\\mcp-ariel-memory"
    }
  }
}
```
