# Общие компоненты — shared/

## MemoryCache (`shared/cache.py`)

LRU кэш с TTL.

```python
from shared.cache import MemoryCache

cache = MemoryCache(max_size=1000, ttl=300)
cache.set("user:alice:context", {"facts": [...]})
cache.get("user:alice:context")
cache.delete("user:alice:context")
cache.clear()
cache.size()
```

## DBPool (`shared/db_pool.py`)

Пул соединений SQLite.

```python
from shared.db_pool import DBPool

pool = DBPool()
conn = pool.get("core_memory.db")
pool.stats()
pool.close_all()
```

## Saga + Watchdog (`shared/saga.py`)

Паттерн для многошаговых операций с компенсацией (откат). Persistence на диск + watchdog + timeout.

```python
from shared.saga import Saga, saga_watchdog, create_consolidation_saga, create_backup_saga

# Готовые саги
saga = create_consolidation_saga(user_id="alice")
result = await saga.execute({"user_id": "alice"})
print(saga.status.value)  # "completed" или "compensated"
print(saga.get_state())   # {"saga_id": "consolidation_alice_abc123", ...}

# Saga с таймаутом
saga = Saga("my_saga", timeout_seconds=60)
saga.add_step("step1", action_fn, compensation_fn)
await saga.execute()
```

### Watchdog

```python
from shared.saga import saga_watchdog

saga_watchdog.start()  # фоновый поток проверяет каждые 60 сек
stuck = saga_watchdog.get_stuck_sagas()    # зависшие саги
saga_watchdog.recover_saga("saga_id")      # восстановить
saga_watchdog.cleanup_completed()          # удалить завершённые > 1ч
```

### Кастомная сага

```python
async def step_action(data: dict) -> dict:
    return {"result": "ok"}

async def step_compensation(data: dict) -> None:
    pass

saga = Saga("my_workflow", timeout_seconds=120)
saga.add_step("step1", step_action, step_compensation)
saga.add_step("step2", step_action, step_compensation)
result = await saga.execute({"input": "value"})
```

## Middleware (`shared/middleware.py`)

Цепочка обработчиков для перехвата MCP запросов.

```python
from shared.middleware import MiddlewarePipeline, MiddlewareContext, ValidationMiddleware, RateLimitMiddleware

pipeline = MiddlewarePipeline()
pipeline.add(ValidationMiddleware())
pipeline.add(RateLimitMiddleware(max_per_minute=100))

ctx = MiddlewareContext(tool_name="memory_user_remember", user_id="alice", args={"key": "k", "value": "v"})
result = await pipeline.execute(ctx, handler)
```

**Middleware:**

| Middleware | Описание |
|-----------|----------|
| `ValidationMiddleware` | Валидация параметров |
| `RateLimitMiddleware` | Ограничение частоты (100/min per user) |
| `ImportanceGateMiddleware` | Фильтр шума (порог 0.3, regex паттерны) |
| `AuditMiddleware` | Логирование всех вызовов |
| `DedupMiddleware` | Дедупликация запросов (5 сек окно) |

## EmbeddingCache (`shared/embeddings.py`)

Кэш эмбеддингов (SHA-256 → blob) в SQLite. Мультиязычная модель `intfloat/multilingual-e5-small` (100+ языков, включая русский). Нормализация текста перед хешированием (lowercase, убрать пунктуацию).

```python
from shared.embeddings import EmbeddingCache, embed_text, similarity, DEFAULT_MODEL

print(DEFAULT_MODEL)  # "intfloat/multilingual-e5-small"

cache = EmbeddingCache()
emb1 = cache.embed_single("Привет мир")   # русский — работает!
emb2 = cache.embed_single("Hello world")  # английский — тоже

# Нормализация: "Python is great" и "Python is great!" дают одинаковый кэш
h1 = cache._hash_text("Python is great")
h2 = cache._hash_text("Python is great!")
assert h1 == h2  # одинаковый хэш!

cache.count()

# Кастомная модель
cache2 = EmbeddingCache(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

similarity(emb1, emb2)  # cosine similarity
```

## Metrics (`shared/metrics.py`)

Prometheus-compatible метрики.

```python
from shared.metrics import metrics

metrics.inc("tool_calls")
metrics.gauge("active_users", 5)
metrics.histogram("latency", 0.1)

metrics.render_prometheus()  # Prometheus формат
metrics.render_json()        # JSON формат
```

## DreamBuffer (`shared/dream_buffer.py`)

Промежуточное хранилище (staging_memories) перед консолидацией. TTL + auto-cleanup.

```python
from shared.dream_buffer import DreamBuffer

db = DreamBuffer()
db.add(user_id="alice", session_id="sess1", content="User likes Python", importance=0.6)
items = db.get_staging("alice")
db.count("alice")
db.count_all()

# Очистка: > 24ч или > 500 записей
db.cleanup_old(max_age_hours=24, max_count=500)
# {"by_age": 12, "by_count": 3}

db.clear_staging("alice")
```

## ArchivedMemories (`shared/archived_memories.py`)

Хранилище архивированных записей. Можно восстановить.

```python
from shared.archived_memories import ArchivedMemories

am = ArchivedMemories()
am.archive("alice", "Old memory about project X", importance=0.2, reason="inactive_30d")
archived = am.get_archived("alice", limit=50)
am.count("alice")

restored = am.restore(archived_id=42)
# {"content": "Old memory...", "memory_type": None, "importance": 0.2}
```

## Migrations (`shared/migrations.py`)

Система миграций схемы БД. Версионирование: каждая миграция имеет номер.

```python
from shared.migrations import migration_manager

# Применить недостающие миграции при старте
result = migration_manager.migrate()
# {"current_version": 0, "applied": [{"version": 1, "name": "init_schema"}, ...], "new_version": 3}

# Текущая версия
version = migration_manager.get_current_version()  # 3

# Ожидающие миграции
pending = migration_manager.get_pending()
```

**Добавление новой миграции:**

```python
from shared.migrations import Migration, _get_migrations

def v4_add_field(conn):
    try:
        conn.execute("ALTER TABLE staging_memories ADD COLUMN emotional_vector BLOB")
    except sqlite3.OperationalError:
        pass

_get_migrations().append(Migration(4, "add_emotional_vector", v4_add_field))
```

**Текущие миграции:**

| Версия | Имя | Описание |
|--------|-----|----------|
| 1 | `init_schema` | Начальная схема всех таблиц |
| 2 | `add_conflict_fields` | is_conflict + conflict_group_id |
| 3 | `add_wiki_source` | source column в wiki таблицах |

## ReadOnlyReplica (`shared/read_only.py`)

Read-only копия БД для dashboard/metrics/ревизии без нагрузки на основную БД.

```python
from shared.read_only import read_only_replica

# Запустить авто-синхронизацию (каждые 5 мин)
read_only_replica.start_auto_sync(interval_seconds=300)

# Ручная синхронизация
read_only_replica.sync()
# {"core_memory.db": 1, "episodic.db": 1, ...}

# Read-only соединение
conn = read_only_replica.get_conn("core_memory.db")

# Проверка готовности
read_only_replica.is_ready()  # True если replica существует
```

**Как работает:**
- SQLite backup API для безопасного копирования
- Auto-sync каждые 5 минут
- Read-only URI (`?mode=ro`) — нет нагрузки на основную БД
