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

Persistence на диск + watchdog + per-step timeout + вложенные саги + компенсация.

```python
from shared.saga import Saga, saga_watchdog

# Сaga с timeout
saga = Saga("backup", timeout_seconds=60)

# Step с кастомным timeout
saga.add_step("copy", copy_fn, compensate_fn, timeout_seconds=30)
saga.add_step("verify", verify_fn, timeout_seconds=10)
saga.add_step("default", default_fn)  # timeout саги (60s)

# Вложенная сага
inner = Saga("inner")
inner.add_step("inner_step", inner_action, inner_compensate)
saga.add_step("inner_saga", inner)

# Async функции в шагах — поддерживаются автоматически
async def async_step(data):
    return {"result": "ok"}
saga.add_step("async_step", async_step)

# Выполнение
result = await saga.execute({"user_id": "alice"})

# Watchdog
saga_watchdog.start()
saga_watchdog.get_stuck_sagas()
saga_watchdog.recover_saga("saga_id")
saga_watchdog.cleanup_completed()
```

**Компенсация:**
- Если шаг упал → откат предыдущих шагов
- Если вложенная сага завершилась → её шаги НЕ компенсируются
- Если outer сага упала после inner → inner компенсируется

### Готовые саги

```python
from shared.saga import create_consolidation_saga, create_backup_saga

# Консолидация: gather → distill → promote
saga = create_consolidation_saga(user_id="alice", mm=memory_manager)
result = await saga.execute({"user_id": "alice", "_mm": memory_manager})

# Бэкап: copy → verify
saga = create_backup_saga()
result = await saga.execute()
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

Кэш эмбеддингов (SHA-256 → blob) в SQLite. Мультиязычная модель `intfloat/multilingual-e5-small` (100+ языков). Нормализация текста перед хешированием.

```python
from shared.embeddings import EmbeddingCache, embed_text, embed_texts, similarity, DEFAULT_MODEL

print(DEFAULT_MODEL)  # "intfloat/multilingual-e5-small"

cache = EmbeddingCache()
emb = await cache.embed_single("Привет мир")  # русский работает!
emb = await cache.embed_single("Hello world")  # английский тоже

# Нормализация: "Python is great" и "Python is great!" дают одинаковый кэш
h1 = cache._hash_text("Python is great")
h2 = cache._hash_text("Python is great!")
assert h1 == h2

# Пакетное вычисление
embeddings = await embed_texts(["text1", "text2"])

# Similarity
similarity(emb1, emb2)  # cosine similarity
```

## Metrics (`shared/metrics.py`)

MetricsCollector — Prometheus-compatible метрики. Thread-safe. Counters, gauges, histograms.

```python
from shared.metrics import metrics

metrics.inc("tool_calls")           # counter +1
metrics.inc("tool_user_remember")   # counter +1
metrics.gauge("active_users", 5)    # gauge set
metrics.histogram("latency", 0.1)   # histogram observe

metrics.render_prometheus()  # Prometheus text format
metrics.render_json()        # JSON format
```

**Prometheus формат (каждый вызов):**
```
# HELP ariel_memory_uptime_seconds Server uptime
# TYPE ariel_memory_uptime_seconds gauge
ariel_memory_uptime_seconds 3600.0
# TYPE ariel_memory_tool_calls counter
ariel_memory_tool_calls 42
# TYPE ariel_memory_latency_summary summary
ariel_memory_latency_summary{quantile="0.5"} 0.12
ariel_memory_latency_summary{quantile="0.9"} 0.18
ariel_memory_latency_count 42
```

## ArchivedMemories (`shared/archived_memories.py`)

Архив с восстановлением. Единый путь для всех архиваций (forgetting, consolidation).

```python
from shared.archived_memories import ArchivedMemories

am = ArchivedMemories()
await am.archive("alice", "Old memory", importance=0.2, reason="inactive_30d")
archived = await am.get_archived("alice", limit=50)

# Восстановить
restored = await am.restore(archived_id=42)
# {"content": "Old memory...", "importance": 0.2}

await am.count("alice")
```

**Используется:**
- `forgetting.archive_old_entries()` — архивация старых записей
- `consolidation.consolidate_staging()` — архивация staging

## ReadOnlyReplica (`shared/read_only.py`)

Read-only копия БД для dashboard/metrics. Автоматически синхронизируется при старте.

```python
from shared.read_only import read_only_replica
await asyncio.to_thread(read_only_replica.sync)  # при старте
read_only_replica.sync()  # ручная синхронизация
conn = read_only_replica.get_conn("memory.db")  # read-only URI
read_only_replica.is_ready()
```

## MemoryCache (`shared/cache.py`)

LRU кэш с TTL. Интегрирован с MemoryManager — `recall()` кэширует результаты.

```python
from shared.cache import MemoryCache

cache = MemoryCache(max_size=1000, ttl=300)
cache.set("user:alice:context", {"facts": [...]})
cache.get("user:alice:context")
cache.delete("user:alice:context")
cache.clear()
cache.size()
```

**Интеграция с MemoryManager:**
```python
mm = MemoryManager(cache=MemoryCache())
# recall() автоматически кэширует результаты (TTL 300с)
```
