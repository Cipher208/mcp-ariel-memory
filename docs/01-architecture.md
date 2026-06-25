# Архитектура

## Стек

| Компонент | Технология |
|-----------|-----------|
| MCP протокол | Python MCP SDK v1.28 (FastMCP) |
| Транспорты | stdio + Streamable HTTP |
| Хранилище | SQLite (WAL mode) |
| Async DB | **aiosqlite** через AsyncConnectionManager |
| Поиск | FTS5 + sqlite-vec (опционально) |
| Docker | Dockerfile + docker-compose |
| Тесты | pytest + pytest-asyncio |
| CI/CD | GitHub Actions |

## Двухслойная модель

```
┌─────────────────────────────────────────────────────┐
│               MCP Server (31 async tools)            │
│  FastMCP + stdio/HTTP transports + auth              │
├──────────────────────┬──────────────────────────────┤
│   Layer 1: User      │   Layer 2: Agent             │
│   Факты о пользователе│   Личность агента           │
├──────────────────────┼──────────────────────────────┤
│ L1 ReflexBuffer      │ L1 AgentBuffer               │
│ L2 SessionStore      │ L2 AgentSession              │
│ L3 EpisodicMemory    │ L3 AgentEpisodic             │
│ L4 CoreMemory        │ L4 AgentCore                 │
│ RAG (wiki user)      │ RAG (wiki agent)             │
│ Graph (user)         │ Graph (agent + tags)         │
│ Hooks (user events)  │ Hooks (agent events)         │
├──────────────────────┴──────────────────────────────┤
│ Features: Auth | Backup | Dashboard | Metrics       │
│ Shared: Cache | Saga | Middleware | Embeddings       │
└─────────────────────────────────────────────────────┘
```

## Иерархия L1 → L4

| Уровень | Назначение | Хранилище | Лимит |
|---------|-----------|-----------|-------|
| **L1 ReflexBuffer** | Последние сообщения (кольцевой буфер) | RAM + JSON | 50 |
| **L2 SessionStore** | История сессий с индексами | SQLite | 100 |
| **L3 EpisodicMemory** | Важные моменты с эмоциональным весом | SQLite | 1000 |
| **L4 CoreMemory** | Ключ-значение факты с важностью | SQLite | 5000 |

## Консолидация

```
Сообщение → L1 (буфер)
           → ImportanceGate (фильтр шума, порог 0.3)
           → L2 (сессия)
           → EmotionTrigger (эмоциональный анализ)
           → L3 (эпизоды, если важность > 0.7)
           → L4 (консолидация, если вес > 0.7)
```

## Директория хранения

```
~/.mcp-ariel-memory/
├── core_memory.db      # L4: ключ-значение факты
├── episodic.db         # L3: эпизоды
├── sessions.db         # L2: сессии
├── rag.db              # RAG: wiki + FTS5
├── graph.db            # Граф: эпистемический + временной
├── wiki_index.db       # Wiki: индекс .md файлов
├── cognitive.db        # DreamBuffer + ArchivedMemories
├── embedding_cache.db  # Кэш эмбеддингов
├── audit.db            # Аудит
├── wiki/               # .md файлы wiki (source of truth)
│   ├── user/           # User wiki
│   └── agent/          # Agent wiki
├── sagas/              # Состояние саг (persistence)
├── backups/            # Бэкапы
├── archives/           # Архив аудита
└── exports/            # Экспорт данных
```
