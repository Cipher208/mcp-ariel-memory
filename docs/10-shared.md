# Общие компоненты — shared/

## AsyncConnectionManager (`shared/connection.py`)

Нативный async менеджер соединений SQLite. Один коннект к **`memory.db`** (~25 таблиц). WAL + busy_timeout, stale-check.

```python
from shared.connection import AsyncConnectionManager, connection_manager

# Получить соединение
conn = await connection_manager.get("memory.db")

# Все операции — async
cursor = await conn.execute("SELECT * FROM users WHERE id=?", (uid,))
row = await cursor.fetchone()
await conn.commit()
```

**Таблицы в memory.db:**
core_memory, sessions, episodes, staging_memories, archived_memories, audit_log, rate_limits, embedding_cache, rag_pages, rag_chunks, rag_relations, rag_fts, epi_nodes, epi_edges, temporal_events, temporal_links, user_wiki, agent_wiki, user_wiki_fts, agent_wiki_fts, wiki_index, wiki_fts, memory_conflicts, migration_log

## MemoryCache (`shared/cache.py`)

LRU кэш с TTL.

```python
from shared.cache import MemoryCache
cache = MemoryCache(max_size=1000, ttl=300)
cache.set("key", "value")
cache.get("key")
cache.size()
```

## DBPool (`shared/db_pool.py`)

Пул соединений SQLite.

## Saga + Watchdog (`shared/saga.py`)

Persistence на диск + watchdog + timeout + recovery.

```python
from shared.saga import Saga, saga_watchdog
saga = Saga("backup", timeout_seconds=60)
saga.add_step("copy", copy_fn, compensate_fn)
await saga.execute()
saga_watchdog.start()
saga_watchdog.get_stuck_sagas()
saga_watchdog.cleanup_completed()
```

## Middleware (`shared/middleware.py`)

Цепочка: Validation → RateLimit → ImportanceGate → Audit → Dedup.

```python
from shared.middleware import MiddlewarePipeline, MiddlewareContext, ValidationMiddleware
pipeline = MiddlewarePipeline()
pipeline.add(ValidationMiddleware())
result = await pipeline.execute(ctx, handler)
```

## EmbeddingCache (`shared/embeddings.py`)

Мультиязычная модель `intfloat/multilingual-e5-small` (100+ языков). Нормализация текста перед хешированием.

```python
from shared.embeddings import EmbeddingCache, embed_text, similarity, DEFAULT_MODEL
ec = EmbeddingCache()
emb = ec.embed_single("Привет мир")  # русский работает!
h1 = ec._hash_text("Python is great")
h2 = ec._hash_text("Python is great!")
assert h1 == h2  # нормализация!
```

## Metrics (`shared/metrics.py`)

Prometheus-compatible метрики.

## DreamBuffer (`shared/dream_buffer.py`)

Staging с TTL + auto-cleanup (24ч / 500 записей).

```python
from shared.dream_buffer import DreamBuffer
db = DreamBuffer()
db.add("alice", "s1", "msg", 0.5)
db.cleanup_old(max_age_hours=24, max_count=500)
```

## ArchivedMemories (`shared/archived_memories.py`)

Архив с восстановлением.

## Migrations (`shared/migrations.py`)

Версионирование схемы БД. 3 миграции.

```python
from shared.migrations import migration_manager
migration_manager.migrate()  # {"current_version": 0, "new_version": 3}
```

## ReadOnlyReplica (`shared/read_only.py`)

Read-only копия БД для dashboard/metrics.

```python
from shared.read_only import read_only_replica
read_only_replica.start_auto_sync(interval_seconds=300)
read_only_replica.sync()  # {"core_memory.db": 1, ...}
conn = read_only_replica.get_conn("core_memory.db")
```
