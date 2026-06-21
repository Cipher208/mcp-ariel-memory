# Тестирование и структура проекта

## Тестирование

```bash
# Все тесты (49 tests)
python -m pytest tests/ -v

# Только модульные тесты
python -m pytest tests/test_core/ tests/test_rag/ tests/test_graph/ -v

# MCP Inspector
uv run mcp dev mcp_server.py
```

**Статус:** 49/49 pytest + 31/31 MCP tools.

## Структура тестов

```
tests/
├── test_all.py              # 10 legacy tests (обратная совместимость)
├── test_core/               # 6 tests: ReflexBuffer, SessionStore, Episodic, Core, MemoryManager
├── test_rag/                # 5 tests: RAGEngine, RRF, Router, Conflict
├── test_graph/              # 4 tests: Epistemic, Temporal
├── test_lifecycle/          # 3 tests: Forgetting, Emotion, Consolidation
├── test_hooks/              # 3 tests: Registry, UserHooks, AgentHooks
├── test_wiki/               # 3 tests: FileWiki add/search/count
├── test_features/           # 6 tests: Audit, RateLimit, Backup, ImportExport, Compression
├── test_shared/             # 6 tests: Cache, DreamBuffer, Archive, Embeddings, Metrics, Middleware
└── test_mcp/                # 3 tests: Tools count, async, backward compat
```

## Структура проекта

```
mcp-ariel-memory/
├── pyproject.toml           # Конфигурация пакета
├── Dockerfile               # Docker образ
├── docker-compose.yml       # Docker Compose
├── .github/workflows/ci.yml # CI/CD
├── config.yaml              # Единый конфиг
├── config.py                # Загрузчик конфига
├── __init__.py              # Корневой пакет
├── __main__.py              # Точка входа
├── mcp_server.py            # MCP SDK сервер (31 async tool) — ОСНОВНОЙ
├── server.py                # Legacy (обратная совместимость, НЕ для MCP)
├── docs/                    # Документация
│   ├── 00-index.md          # Оглавление
│   ├── 01-architecture.md   # Архитектура
│   ├── 02-mcp-tools.md      # MCP Tools
│   ├── 03-core.md           # Ядро памяти
│   ├── 04-rag.md            # Поиск
│   ├── 05-graph.md          # Граф знаний
│   ├── 06-lifecycle.md      # Жизненный цикл
│   ├── 07-hooks.md          # Хуки
│   ├── 08-wiki.md           # Wiki
│   ├── 09-features.md       # Фичи
│   ├── 10-shared.md         # Общие компоненты
│   ├── 11-operations.md     # Операции
│   └── 12-testing.md        # Тестирование
├── tests/
│   └── test_all.py          # pytest тесты
├── core/                    # L1-L4 ядро памяти
│   ├── __init__.py          # MemoryManager
│   ├── reflex.py            # L1: ReflexBuffer
│   ├── session.py           # L2: SessionStore
│   ├── episodic.py          # L3: EpisodicMemory
│   └── memory.py            # L4: CoreMemory
├── rag/                     # Гибридный поиск (FTS5 + RRF)
│   ├── __init__.py
│   ├── engine.py            # RAGEngine
│   ├── router.py            # RetrievalRouter
│   └── conflict.py          # ConflictResolver
├── graph/                   # Граф знаний
│   ├── __init__.py
│   ├── epistemic.py         # EpistemicGraph
│   └── temporal.py          # TemporalGraph
├── lifecycle/               # Жизненный цикл
│   ├── __init__.py
│   ├── forgetting.py        # ForgettingSystem
│   ├── emotion_trigger.py   # EmotionTrigger
│   └── consolidation.py     # ConsolidationEngine
├── hooks/                   # 24 хука
│   ├── __init__.py
│   ├── registry.py          # HookRegistry
│   ├── user_hooks.py        # 12 user hooks
│   └── agent_hooks.py       # 12 agent hooks
├── wiki/                    # Wiki (FileWiki + legacy)
│   ├── __init__.py
│   ├── file_wiki.py         # FileWiki (основной)
│   ├── user_wiki.py         # Legacy (обратная совместимость)
│   └── agent_wiki.py        # Legacy (обратная совместимость)
├── features/                # Доп. фичи
│   ├── __init__.py
│   ├── auth.py              # API keys + Bearer token
│   ├── backup.py            # Бэкапы
│   ├── backup_cron.py       # Автобэкап по расписанию
│   ├── dashboard.py         # HTML дашборд
│   ├── import_export.py     # Импорт/экспорт
│   ├── audit_trail.py       # Аудит (с ротацией)
│   ├── compression.py       # Сжатие
│   └── rate_limiting.py     # Rate limiting
└── shared/                  # Общие компоненты
    ├── __init__.py
    ├── cache.py             # LRU Cache
    ├── db_pool.py           # DB Pool
    ├── embeddings.py        # Embeddings (multilingual + cache)
    ├── metrics.py           # Prometheus метрики
    ├── saga.py              # Saga + Watchdog + Persistence
    ├── middleware.py         # Middleware Pipeline
    ├── dream_buffer.py      # DreamBuffer (staging + TTL)
    └── archived_memories.py # ArchivedMemories
```

**Итого:** 50+ файлов, 31 MCP tool (async, MCP SDK), 24 хука, 14 wiki типов, внешние папки, RRF, saga+watchdog, middleware, dashboard+auth, metrics, backup cron, DreamBuffer TTL, AuditTrail rotation, memory_cleanup, Docker, CI/CD, pytest.
