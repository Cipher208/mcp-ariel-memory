# План: MCP SDK + Async миграция

## Цель
Обернуть mcp-ariel-memory в реальный MCP Python SDK, добавить async, поддерживать stdio + HTTP транспорты.

## Фаза 1: Установка MCP SDK + структура
- [ ] `pip install "mcp[cli]"` или `uv add "mcp[cli]"`
- [ ] Создать `__main__.py` — точка входа для MCP server
- [ ] Создать `mcp_server.py` — FastMCP сервер с декораторами

## Фаза 2: Async миграция core модулей
- [ ] `core/memory.py` — обернуть SQLite в `asyncio.to_thread`
- [ ] `core/session.py` — обернуть SQLite в `asyncio.to_thread`
- [ ] `core/episodic.py` — обернуть SQLite в `asyncio.to_thread`
- [ ] `core/reflex.py` — уже thread-safe, оставить как есть
- [ ] `rag/engine.py` — обернуть SQLite в `asyncio.to_thread`
- [ ] `rag/conflict.py` — обернуть SQLite в `asyncio.to_thread`
- [ ] `graph/epistemic.py` — обернуть SQLite в `asyncio.to_thread`
- [ ] `graph/temporal.py` — обернуть SQLite в `asyncio.to_thread`
- [ ] `wiki/user_wiki.py` — обернуть SQLite в `asyncio.to_thread`
- [ ] `wiki/agent_wiki.py` — обернуть SQLite в `asyncio.to_thread`
- [ ] `features/audit_trail.py` — обернуть SQLite в `asyncio.to_thread`

## Фаза 3: MCP Server (mcp_server.py)
- [ ] FastMCP("ariel-memory") с 20 async tools
- [ ] Lifespan: startup (init DB pools) + shutdown (close connections)
- [ ] Context: логирование через ctx.info/ctx.error
- [ ] Structured output: Pydantic модели для ответов

## Фаза 4: Транспорты
- [ ] stdio: `mcp.run(transport="stdio")` — для Claude Desktop
- [ ] HTTP: `mcp.run(transport="streamable-http")` — для веб-клиентов
- [ ] `__main__.py` — CLI: `python -m mcp_ariel_memory --transport stdio|http`

## Фаза 5: Конфигурация Claude Desktop
- [ ] Готовый JSON для `claude_desktop_config.json`
- [ ] Инструкция по установке

## Структура после миграции

```
mcp-ariel-memory/
├── __main__.py          # Точка входа: python -m mcp_ariel_memory
├── mcp_server.py        # FastMCP сервер (20 tools, lifespan, context)
├── server.py            # Старый MemoryMCPServer (обертка для обратной совместимости)
├── config.yaml
├── config.py
├── core/                # L1-L4 (async обертки)
├── rag/                 # RAG (async обертки)
├── graph/               # Граф (async обертки)
├── lifecycle/           # Lifecycle (async обертки)
├── hooks/               # Хуки (async обертки)
├── wiki/                # Wiki (async обертки)
├── features/            # Фичи (async обертки)
├── shared/              # Cache, DB pool
└── README.md
```

## Порядок выполнения

1. Установить MCP SDK
2. Создать mcp_server.py с 20 tools (декораторы)
3. Обернуть core модули в async (to_thread)
4. Подключить к mcp_server.py
5. Добавить __main__.py с CLI
6. Добавить aiosqlite для hotspot путей (episodic.search, core.search)
7. Настроить stdio + HTTP транспорты
8. Обновить README
