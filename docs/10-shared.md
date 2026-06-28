# Shared Components — shared/

All shared modules live in `shared/` and are imported across the mcp-ariel-memory server. They provide connection management, caching, saga orchestration, middleware pipelines, embeddings, metrics, staging/archival storage, migrations, and a read-only replica.

---

## AsyncConnectionManager (`shared/connection.py`)

Unified async SQLite connection manager. One connection per DB file (no pool — aiosqlite's internal queue handles concurrency). WAL mode + busy_timeout for safe concurrent writes.

### Constants

- **`_DEFAULT_DIR`**: `~/.mcp-ariel-memory` (overridable via `MCP_MEMORY_DATA_DIR` env var)

### Class: `AsyncConnectionManager`

```python
class AsyncConnectionManager:
    def __init__(self, base_dir: str = "")
```

Creates the base directory if it doesn't exist.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_dir` | `str` | `""` | Directory for DB files. Falls back to `MCP_MEMORY_DATA_DIR` or `~/.mcp-ariel-memory`. |

### `AsyncConnectionManager.get`

```python
async def get(self, db_name: str = "memory.db") -> aiosqlite.Connection
```

Returns an existing connection to `db_name`, or creates a new one with WAL, busy_timeout=5000, synchronous=NORMAL, foreign_keys=ON. Checks stale connections by executing `SELECT 1`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `db_name` | `str` | `"memory.db"` | Filename relative to `base_dir`. |

**Returns**: `aiosqlite.Connection` with `row_factory = aiosqlite.Row`.

```python
from shared.connection import connection_manager

conn = await connection_manager.get("memory.db")
cursor = await conn.execute("SELECT * FROM core_memory WHERE user_id=?", ("alice",))
row = await cursor.fetchone()
print(row["key"], row["value"])
```

### `AsyncConnectionManager.close_all`

```python
async def close_all(self)
```

Closes all open connections. Call on shutdown.

```python
await connection_manager.close_all()
```

### `AsyncConnectionManager.stats`

```python
def stats(self) -> dict
```

**Returns**: `{"connections": int, "dbs": list[str]}` — number of open connections and their names.

```python
print(connection_manager.stats())
# {"connections": 2, "dbs": ["memory.db", "analytics.db"]}
```

### `AsyncConnectionManager.execute_script`

```python
async def execute_script(self, db_name: str, script: str)
```

Executes a multi-statement SQL script (e.g. `CREATE TABLE IF NOT EXISTS ...`) and commits.

| Parameter | Type | Description |
|-----------|------|-------------|
| `db_name` | `str` | Target DB filename. |
| `script` | `str` | SQL script with multiple statements. |

```python
await connection_manager.execute_script("memory.db", """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL
    );
""")
```

### `AsyncConnectionManager.table_exists`

```python
async def table_exists(self, db_name: str, table: str) -> bool
```

Checks whether a table exists in the given DB.

| Parameter | Type | Description |
|-----------|------|-------------|
| `db_name` | `str` | Target DB filename. |
| `table` | `str` | Table name to check. |

**Returns**: `True` if the table exists, `False` otherwise.

```python
if await connection_manager.table_exists("memory.db", "core_memory"):
    print("Table exists")
```

### `AsyncConnectionManager.vacuum`

```python
async def vacuum(self, db_name: str)
```

Runs `VACUUM` to reclaim disk space after bulk deletions.

| Parameter | Type | Description |
|-----------|------|-------------|
| `db_name` | `str` | Target DB filename. |

```python
await connection_manager.vacuum("memory.db")
```

### Global Instance

```python
from shared.connection import connection_manager
```

Pre-configured `AsyncConnectionManager` using the default directory. Most code should use this directly.

---

## MemoryCache (`shared/cache.py`)

Thread-safe LRU cache with TTL expiration. Used for caching hot data (e.g. `recall()` results).

### Class: `MemoryCache`

```python
class MemoryCache:
    def __init__(self, max_size: int = 1000, ttl: int = 300)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_size` | `int` | `1000` | Maximum entries before LRU eviction. |
| `ttl` | `int` | `300` | Time-to-live in seconds. |

### `MemoryCache.get`

```python
def get(self, key: str) -> Optional[Any]
```

Returns the cached value, or `None` if missing or expired. Moves accessed entries to the end (LRU).

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `str` | Cache key. |

**Returns**: Cached value or `None`.

```python
from shared.cache import MemoryCache

cache = MemoryCache(max_size=100, ttl=60)
cache.set("user:alice", {"facts": ["likes cats"]})
data = cache.get("user:alice")
# {"facts": ["likes cats"]}
```

### `MemoryCache.set`

```python
def set(self, key: str, value: Any)
```

Stores a value. If the cache exceeds `max_size`, the oldest entry is evicted.

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `str` | Cache key. |
| `value` | `Any` | Value to cache. |

```python
cache.set("session:abc", {"messages": [...]})
```

### `MemoryCache.delete`

```python
def delete(self, key: str) -> bool
```

Removes an entry. Returns `True` if the key existed, `False` otherwise.

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `str` | Cache key to remove. |

```python
removed = cache.delete("session:abc")
# True
```

### `MemoryCache.clear`

```python
def clear(self)
```

Removes all entries.

```python
cache.clear()
```

### `MemoryCache.size`

```python
def size(self) -> int
```

**Returns**: Number of entries currently in the cache.

```python
print(cache.size())  # 0
```

---

## Saga + SagaWatchdog (`shared/saga.py`)

Multi-step operation framework with compensation (rollback), disk persistence, per-step timeout, nested sagas, and a watchdog for detecting stuck sagas.

### Constants

- **`SAGA_DIR`**: `~/.mcp-ariel-memory/sagas/` — state files stored as `<saga_id>.json`.

### Enum: `SagaStatus`

```python
class SagaStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    STUCK = "stuck"  # detected by watchdog
```

### Dataclass: `SagaStep`

```python
@dataclass
class SagaStep:
    name: str
    action: Callable[[dict], Coroutine[Any, Any, dict]]
    compensation: Optional[Callable[[dict], Coroutine[Any, Any, None]]] = None
    timeout_seconds: Optional[int] = None
    status: SagaStatus = SagaStatus.PENDING
    result: dict = field(default_factory=dict)
    data: dict = field(default_factory=dict)
```

### Class: `Saga`

```python
class Saga:
    def __init__(self, name: str, timeout_seconds: int = 300)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | — | Saga name (used in logs and state files). |
| `timeout_seconds` | `int` | `300` | Default timeout per step. |

### `Saga.status` (property)

```python
@property
def status(self) -> SagaStatus
```

Current saga status.

### `Saga.data` (property)

```python
@property
def data(self) -> dict
```

Shared data dict that accumulates step results.

### `Saga.add_step`

```python
def add_step(
    self,
    name: str,
    action: Callable[[dict], Coroutine[Any, Any, dict]],
    compensation: Optional[Callable[[dict], Coroutine[Any, Any, None]]] = None,
    timeout_seconds: Optional[int] = None,
) -> "Saga"
```

Appends a step. Returns `self` for chaining.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | — | Step name. |
| `action` | `Callable[[dict], Coroutine]` | — | Async function receiving `data` dict, returning dict to merge. Can also be another `Saga` instance for nested sagas. |
| `compensation` | `Optional[Callable]` | `None` | Async rollback function (receives `data` dict, returns `None`). |
| `timeout_seconds` | `Optional[int]` | `None` | Per-step timeout. Falls back to saga-level timeout. |

```python
async def do_backup(data):
    # ... backup logic ...
    return {"backup_path": "/backups/2024-01"}

async def undo_backup(data):
    shutil.rmtree(data["backup_path"])

saga = Saga("backup", timeout_seconds=60)
saga.add_step("copy", do_backup, undo_backup, timeout_seconds=30)
saga.add_step("verify", verify_fn)
```

### `Saga.execute`

```python
async def execute(self, initial_data: Optional[dict] = None) -> dict
```

Runs all steps sequentially. On failure, compensates completed steps in reverse order. On success, returns the accumulated data dict and deletes the state file.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `initial_data` | `Optional[dict]` | `None` | Starting data for the saga. |

**Returns**: Final accumulated `data` dict.

**Raises**: The original exception on failure (after compensation).

**Supports**:
- Nested sagas: if `action` is a `Saga` instance, it is executed with the current data.
- Sync callables: if `action` returns a non-awaitable result, it is used directly.

```python
result = await saga.execute({"user_id": "alice"})
# result = {"user_id": "alice", "backup_path": "/backups/2024-01", ...}
```

### `Saga.get_state`

```python
def get_state(self) -> dict
```

**Returns**: Full state dict with `name`, `saga_id`, `status`, `current_step`, `started_at`, `data`, and per-step `status`/`result`.

```python
state = saga.get_state()
print(state["status"])  # "completed"
```

### Class: `SagaWatchdog`

```python
class SagaWatchdog:
    def __init__(self, check_interval: int = 60, max_age_seconds: int = 600)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `check_interval` | `int` | `60` | Seconds between stuck-saga checks. |
| `max_age_seconds` | `int` | `600` | Age threshold for marking a saga as stuck. |

### `SagaWatchdog.start`

```python
def start(self)
```

Starts the background watchdog thread. No-op if already running.

```python
saga_watchdog.start()
```

### `SagaWatchdog.stop`

```python
def stop(self)
```

Stops the watchdog thread (waits up to 5 seconds).

```python
saga_watchdog.stop()
```

### `SagaWatchdog.get_stuck_sagas`

```python
def get_stuck_sagas(self) -> List[Dict[str, Any]]
```

**Returns**: List of dicts with keys `saga_id`, `name`, `status`, `current_step`, `age_seconds` for all stuck/failed/running sagas.

```python
stuck = saga_watchdog.get_stuck_sagas()
for s in stuck:
    print(f"{s['name']}: {s['status']} (age={s['age_seconds']}s)")
```

### `SagaWatchdog.recover_saga`

```python
def recover_saga(self, saga_id: str) -> Optional[Dict[str, Any]]
```

Marks a stuck saga for manual review.

| Parameter | Type | Description |
|-----------|------|-------------|
| `saga_id` | `str` | The saga ID to recover. |

**Returns**: `{"status": "manual_review_required", "state": ...}` or error dict. `None` if file doesn't exist.

```python
result = saga_watchdog.recover_saga("backup_abc123")
# {"status": "manual_review_required", "state": {...}}
```

### `SagaWatchdog.cleanup_completed`

```python
def cleanup_completed(self) -> int
```

Deletes state files for completed/compensated sagas older than 1 hour.

**Returns**: Number of files removed.

```python
removed = saga_watchdog.cleanup_completed()
# 3
```

### Global Instance

```python
from shared.saga import saga_watchdog
```

### Pre-built Sagas

#### `create_consolidation_saga`

```python
def create_consolidation_saga(user_id: str, mm=None) -> Saga
```

Three-step saga: gather → distill → promote. Staging memories are gathered, filtered by importance (>0.3), then promoted to core memory.

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | `str` | User ID for scoping. |
| `mm` | `MemoryManager` | Memory manager instance (avoids circular imports). |

```python
from shared.saga import create_consolidation_saga

saga = create_consolidation_saga("alice", mm=memory_manager)
result = await saga.execute({"user_id": "alice", "_mm": memory_manager})
# result = {"staging_count": 5, "distilled_count": 3, "promoted": 3}
```

#### `create_backup_saga`

```python
def create_backup_saga() -> Saga
```

Two-step saga: copy → verify. Copies `memory.db` to `~/.mcp-ariel-memory/backups/saga_<timestamp>/`, then verifies the backup files exist.

```python
from shared.saga import create_backup_saga

saga = create_backup_saga()
result = await saga.execute()
# result = {"backup_path": "...", "verified_files": 1}
```

---

## Middleware (`shared/middleware.py`)

Chain-of-responsibility pipeline for intercepting and modifying tool requests. Default pipeline order: Validation → RateLimit → ImportanceGate → Audit → Dedup.

### Dataclass: `MiddlewareContext`

```python
@dataclass
class MiddlewareContext:
    tool_name: str = ""
    user_id: str = "default"
    args: Dict = field(default_factory=dict)
    result: Any = None
    metadata: Dict = field(default_factory=dict)
    start_time: float = 0.0
    blocked: bool = False
    block_reason: str = ""
```

### Type Alias

```python
MiddlewareNext = Callable[[MiddlewareContext], Any]
```

### Class: `Middleware` (base)

```python
class Middleware:
    name: str = "base"
    async def process(self, ctx: MiddlewareContext, next: MiddlewareNext) -> Any
```

Base class. Override `process` to implement middleware logic. Always call `await next(ctx)` to continue the chain.

### Class: `RateLimitMiddleware`

```python
class RateLimitMiddleware(Middleware):
    name = "rate_limit"
    def __init__(self, max_per_minute: int = 100)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_per_minute` | `int` | `100` | Max requests per user per 60-second window. |

Blocks requests when the limit is exceeded. Sets `ctx.blocked = True`.

```python
from shared.middleware import RateLimitMiddleware

rl = RateLimitMiddleware(max_per_minute=50)
# User with 50 requests in last minute gets blocked
```

### Class: `AuditMiddleware`

```python
class AuditMiddleware(Middleware):
    name = "audit"
```

Logs tool name, user ID, and elapsed time. Stores elapsed time in `ctx.metadata["elapsed"]`.

```python
from shared.middleware import AuditMiddleware
# Output: "Tool call: memory_user_remember (user=alice)"
# Output: "Tool completed: memory_user_remember in 0.042s"
```

### Class: `ImportanceGateMiddleware`

```python
class ImportanceGateMiddleware(Middleware):
    def __init__(self, min_length: int = 15, threshold: float = 0.3,
                 technical_weight: float = 0.3, question_weight: float = 0.2)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_length` | `int` | `15` | Minimum text length for importance bonus. |
| `threshold` | `float` | `0.3` | Minimum importance score to pass. |
| `technical_weight` | `float` | `0.3` | Bonus for technical keywords. |
| `question_weight` | `float` | `0.2` | Bonus for questions. |

Only active for `memory_user_remember`, `memory_agent_remember`, `memory_user_episode_save`, `memory_agent_episode_save`. Filters out low-importance content.

### `ImportanceGateMiddleware.calculate_score`

```python
def calculate_score(self, text: str) -> float
```

Full importance calculation. Factors: length, questions, technical keywords, line breaks, numbers. Returns 0.0–1.0.

| Parameter | Type | Description |
|-----------|------|-------------|
| `text` | `str` | Content to score. |

**Returns**: Float between 0.0 and 1.0.

```python
gate = ImportanceGateMiddleware()
score = gate.calculate_score("Bug in the API endpoint handler")
# 0.8 (length bonus + technical keywords)
score = gate.calculate_score("ok")
# 0.1 (noise pattern)
```

### Class: `ValidationMiddleware`

```python
class ValidationMiddleware(Middleware):
    name = "validation"
```

Validates that `user_id` is present and `key` is present for remember operations. Blocks invalid requests.

### Class: `DedupMiddleware`

```python
class DedupMiddleware(Middleware):
    name = "dedup"
    def __init__(self, window_seconds: int = 5)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `window_seconds` | `int` | `5` | Deduplication window in seconds. |

Deduplicates identical requests (same user + tool + args) within the window.

### Class: `MiddlewarePipeline`

```python
class MiddlewarePipeline:
    def __init__(self)
```

### `MiddlewarePipeline.add`

```python
def add(self, middleware: Middleware) -> "MiddlewarePipeline"
```

Appends a middleware. Returns `self` for chaining.

| Parameter | Type | Description |
|-----------|------|-------------|
| `middleware` | `Middleware` | Middleware instance. |

### `MiddlewarePipeline.execute`

```python
async def execute(self, ctx: MiddlewareContext, handler: Callable) -> Any
```

Runs the full pipeline. Each middleware calls `next(ctx)` to continue. The `handler` is the actual tool function.

| Parameter | Type | Description |
|-----------|------|-------------|
| `ctx` | `MiddlewareContext` | Request context. |
| `handler` | `Callable` | The function to execute after all middleware. |

**Returns**: Result from the handler (or middleware intercept).

```python
from shared.middleware import MiddlewarePipeline, MiddlewareContext, ValidationMiddleware

pipeline = MiddlewarePipeline()
pipeline.add(ValidationMiddleware())

ctx = MiddlewareContext(tool_name="memory_user_remember", user_id="alice", args={"key": "test"})
result = await pipeline.execute(ctx, my_handler)
```

### `MiddlewarePipeline.list_middlewares`

```python
def list_middlewares(self) -> List[str]
```

**Returns**: List of middleware names in order.

```python
print(pipeline.list_middlewares())
# ["validation", "rate_limit", "importance_gate", "audit", "dedup"]
```

### Global Instance

```python
from shared.middleware import default_pipeline
```

Pre-configured pipeline with Validation → RateLimit → ImportanceGate → Audit → Dedup.

---

## EmbeddingCache (`shared/embeddings.py`)

Async embedding cache with SQLite persistence and multilingual support. Uses `intfloat/multilingual-e5-small` (384 dimensions, 100+ languages).

### Constants

- **`DEFAULT_MODEL`**: `"intfloat/multilingual-e5-small"`

### Class: `EmbeddingCache`

```python
class EmbeddingCache:
    def __init__(self, cm: Optional["AsyncConnectionManager"] = None, model_name: str = None)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cm` | `Optional[AsyncConnectionManager]` | `None` | Connection manager. Falls back to global `connection_manager`. |
| `model_name` | `str` | `None` | Model name. Defaults to `DEFAULT_MODEL`. |

### `EmbeddingCache.embed`

```python
async def embed(self, texts: List[str]) -> List[List[float]]
```

Computes embeddings for a list of texts. Returns cached results when available. Falls back to hash-based embeddings if `sentence_transformers` is not installed.

| Parameter | Type | Description |
|-----------|------|-------------|
| `texts` | `List[str]` | Texts to embed. |

**Returns**: List of 384-dimensional float vectors.

```python
from shared.embeddings import EmbeddingCache

cache = EmbeddingCache()
embeddings = await cache.embed(["Hello world", "Привет мир"])
# [[0.12, -0.03, ...], [0.08, 0.15, ...]]
```

### `EmbeddingCache.embed_single`

```python
async def embed_single(self, text: str) -> List[float]
```

Convenience wrapper for single-text embedding.

| Parameter | Type | Description |
|-----------|------|-------------|
| `text` | `str` | Text to embed. |

**Returns**: 384-dimensional float vector.

```python
emb = await cache.embed_single("What is machine learning?")
# [0.12, -0.03, 0.07, ...]
```

### `EmbeddingCache.count`

```python
async def count(self) -> int
```

**Returns**: Number of cached embeddings in the database.

```python
print(await cache.count())  # 1247
```

### Module-level Functions

#### `embed_text`

```python
async def embed_text(text: str) -> List[float]
```

Shorthand using a fresh `EmbeddingCache()`.

```python
from shared.embeddings import embed_text

emb = await embed_text("Hello world")
```

#### `embed_texts`

```python
async def embed_texts(texts: List[str]) -> List[List[float]]
```

Shorthand for batch embedding using a fresh `EmbeddingCache()`.

```python
from shared.embeddings import embed_texts

embeddings = await embed_texts(["text1", "text2", "text3"])
```

#### `similarity`

```python
def similarity(a: List[float], b: List[float]) -> float
```

Cosine similarity between two vectors.

| Parameter | Type | Description |
|-----------|------|-------------|
| `a` | `List[float]` | First vector. |
| `b` | `List[float]` | Second vector. |

**Returns**: Float between -1.0 and 1.0. Returns 0.0 for zero vectors or non-finite values.

```python
from shared.embeddings import similarity, embed_text

emb1 = await embed_text("cats")
emb2 = await embed_text("kittens")
sim = similarity(emb1, emb2)
# 0.72 (high similarity)
```

---

## MetricsCollector (`shared/metrics.py`)

Prometheus-compatible metrics collection. Thread-safe with counters, gauges, and histograms.

### Class: `MetricsCollector`

```python
class MetricsCollector:
    def __init__(self)
```

### `MetricsCollector.inc`

```python
def inc(self, name: str, value: int = 1)
```

Increments a counter by `value`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | — | Counter name. |
| `value` | `int` | `1` | Increment amount. |

```python
from shared.metrics import metrics

metrics.inc("tool_calls")
metrics.inc("errors", 3)
```

### `MetricsCollector.gauge`

```python
def gauge(self, name: str, value: float)
```

Sets a gauge value.

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Gauge name. |
| `value` | `float` | Gauge value. |

```python
metrics.gauge("active_users", 5)
```

### `MetricsCollector.histogram`

```python
def histogram(self, name: str, value: float)
```

Records a histogram observation. Trims to last 500 entries when exceeding 1000.

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Histogram name. |
| `value` | `float` | Observation value. |

```python
metrics.histogram("latency", 0.12)
```

### `MetricsCollector.render_prometheus`

```python
def render_prometheus(self) -> str
```

**Returns**: Prometheus text format string with uptime, counters, gauges, and histogram summaries (p50/p90/p99).

```python
print(metrics.render_prometheus())
# # HELP ariel_memory_uptime_seconds Server uptime
# # TYPE ariel_memory_uptime_seconds gauge
# ariel_memory_uptime_seconds 3600.0
# # TYPE ariel_memory_tool_calls counter
# ariel_memory_tool_calls 42
```

### `MetricsCollector.render_json`

```python
def render_json(self) -> Dict[str, Any]
```

**Returns**: Dict with `uptime_seconds`, `counters`, `gauges`, and `histograms` (each with `count`, `sum`, `avg`).

```python
data = metrics.render_json()
print(data["uptime_seconds"])  # 3600.0
print(data["counters"]["tool_calls"])  # 42
```

### Global Instance

```python
from shared.metrics import metrics
```

---

## DreamBuffer (`shared/dream_buffer.py`)

Async staging area for memories before consolidation. Memories sit in the staging table until they are promoted or cleaned up.

### Class: `DreamBuffer`

```python
class DreamBuffer:
    def __init__(self, cm: Optional["AsyncConnectionManager"] = None)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cm` | `Optional[AsyncConnectionManager]` | `None` | Connection manager. Falls back to global `connection_manager`. |

### `DreamBuffer.add`

```python
async def add(
    self, user_id: str, session_id: str, content: str,
    importance: float = 0.5, event_id: str = None, metadata: Dict = None
) -> int
```

Adds a staging memory.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | — | User ID. |
| `session_id` | `str` | — | Session ID. |
| `content` | `str` | — | Memory content. |
| `importance` | `float` | `0.5` | Importance score (0.0–1.0). |
| `event_id` | `str` | `None` | Optional event ID. |
| `metadata` | `Dict` | `None` | Optional metadata dict. |

**Returns**: Row ID of the inserted row.

```python
from shared.dream_buffer import DreamBuffer

buf = DreamBuffer()
row_id = await buf.add(
    user_id="alice",
    session_id="sess_123",
    content="Discussed deployment strategy",
    importance=0.7,
    metadata={"topic": "devops"}
)
# 42
```

### `DreamBuffer.get_staging`

```python
async def get_staging(self, user_id: str = "default", session_id: str = None) -> List[Dict[str, Any]]
```

Returns staging memories for a user, optionally filtered by session.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | `"default"` | User ID. |
| `session_id` | `str` | `None` | Optional session filter. |

**Returns**: List of dicts with `id`, `content`, `importance`, `metadata`.

```python
items = await buf.get_staging("alice")
# [{"id": 42, "content": "Discussed deployment strategy", "importance": 0.7, "metadata": {"topic": "devops"}}]
```

### `DreamBuffer.clear_staging`

```python
async def clear_staging(self, user_id: str = "default", session_id: str = None) -> int
```

Deletes staging memories. Returns the number of deleted rows.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | `"default"` | User ID. |
| `session_id` | `str` | `None` | Optional session filter. |

```python
removed = await buf.clear_staging("alice", session_id="sess_123")
# 5
```

### `DreamBuffer.cleanup_old`

```python
async def cleanup_old(self, max_age_hours: int = 24, max_count: int = 500) -> Dict[str, int]
```

Deletes old staging memories by age and caps per-user count.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_age_hours` | `int` | `24` | Max age in hours. |
| `max_count` | `int` | `500` | Max staging entries per user. |

**Returns**: `{"by_age": int, "by_count": int}` — number removed by each criterion.

```python
result = await buf.cleanup_old(max_age_hours=12, max_count=200)
# {"by_age": 12, "by_count": 8}
```

### `DreamBuffer.count`

```python
async def count(self, user_id: str = "default") -> int
```

**Returns**: Number of staging memories for a user.

```python
print(await buf.count("alice"))  # 15
```

### `DreamBuffer.count_all`

```python
async def count_all(self) -> int
```

**Returns**: Total number of staging memories across all users.

```python
print(await buf.count_all())  # 120
```

---

## ArchivedMemories (`shared/archived_memories.py`)

Persistent archival storage for memories. Supports archiving with reasons and restoration.

### Class: `ArchivedMemories`

```python
class ArchivedMemories:
    def __init__(self, cm: Optional["AsyncConnectionManager"] = None)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cm` | `Optional[AsyncConnectionManager]` | `None` | Connection manager. Falls back to global `connection_manager`. |

### `ArchivedMemories.archive`

```python
async def archive(
    self, user_id: str, content: str, memory_type: str = None,
    importance: float = None, original_id: int = None, reason: str = "manual"
) -> int
```

Archives a memory.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | — | User ID. |
| `content` | `str` | — | Memory content. |
| `memory_type` | `str` | `None` | Optional memory type. |
| `importance` | `float` | `None` | Optional importance score. |
| `original_id` | `int` | `None` | Optional original row ID. |
| `reason` | `str` | `"manual"` | Reason for archival. |

**Returns**: Row ID of the archived entry.

```python
from shared.archived_memories import ArchivedMemories

am = ArchivedMemories()
row_id = await am.archive(
    "alice",
    "Old deployment notes",
    memory_type="technical",
    importance=0.2,
    reason="inactive_30d"
)
# 7
```

### `ArchivedMemories.get_archived`

```python
async def get_archived(self, user_id: str = "default", limit: int = 50) -> List[Dict[str, Any]]
```

Returns archived memories, most recent first.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | `"default"` | User ID. |
| `limit` | `int` | `50` | Max entries to return. |

**Returns**: List of dicts with `id`, `content`, `importance`, `archive_reason`, `archived_at`.

```python
archived = await am.get_archived("alice", limit=10)
# [{"id": 7, "content": "Old deployment notes", "importance": 0.2, ...}]
```

### `ArchivedMemories.count`

```python
async def count(self, user_id: str = "default") -> int
```

**Returns**: Number of archived memories for a user.

```python
print(await am.count("alice"))  # 23
```

### `ArchivedMemories.restore`

```python
async def restore(self, archived_id: int) -> Optional[Dict[str, Any]]
```

Restores (and deletes) an archived memory.

| Parameter | Type | Description |
|-----------|------|-------------|
| `archived_id` | `int` | ID of the archived entry. |

**Returns**: `{"content": str, "importance": float}` or `None` if not found.

```python
restored = await am.restore(archived_id=7)
# {"content": "Old deployment notes", "importance": 0.2}
```

---

## MigrationManager + Migration (`shared/migrations.py`)

Async database migration framework. All migrations defined in a single file with version numbers.

### Constants

- **`DB_NAME`**: `"memory.db"`

### Class: `Migration`

```python
class Migration:
    def __init__(self, version: int, name: str, up: Callable)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `version` | `int` | Migration version number. |
| `name` | `str` | Migration name. |
| `up` | `Callable` | Async function that receives a connection and applies the migration. |

### Class: `MigrationManager`

```python
class MigrationManager:
    def __init__(self, cm: Optional[AsyncConnectionManager] = None)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cm` | `Optional[AsyncConnectionManager]` | `None` | Connection manager. Falls back to global `connection_manager`. |

### `MigrationManager.get_current_version`

```python
async def get_current_version(self) -> int
```

**Returns**: Current schema version from `migration_log`, or `0` if no migrations applied.

```python
from shared.migrations import migration_manager

version = await migration_manager.get_current_version()
# 1
```

### `MigrationManager.migrate`

```python
async def migrate(self) -> Dict[str, Any]
```

Applies all pending migrations in order. Each migration is committed and logged.

**Returns**: `{"current_version": int, "applied": [{"version": int, "name": str}], "new_version": int}`.

```python
result = await migration_manager.migrate()
# {"current_version": 0, "applied": [{"version": 1, "name": "init_unified_schema"}], "new_version": 1}
```

### `MigrationManager.get_pending`

```python
async def get_pending(self) -> List[Dict[str, Any]]
```

**Returns**: List of pending migrations with `version` and `name`.

```python
pending = await migration_manager.get_pending()
# [{"version": 1, "name": "init_unified_schema"}]
```

### Global Instance

```python
from shared.migrations import migration_manager
```

### Schema Tables (v1)

The initial migration creates all tables in `memory.db`:

| Table | Purpose |
|-------|---------|
| `core_memory` | L2-L4 core memories (key-value with importance) |
| `sessions` | Session summaries and state deltas |
| `episodes` | Episode storage with emotional weight |
| `staging_memories` | DreamBuffer staging area |
| `archived_memories` | Archived/forgetten memories |
| `audit_log` | Action audit trail |
| `rate_limits` | Rate limiting timestamps |
| `embedding_cache` | Cached embeddings (SHA-256 → blob) |
| `rag_pages` | RAG page storage |
| `rag_chunks` | RAG chunk storage with embeddings |
| `rag_relations` | RAG page relations |
| `rag_fts` | FTS5 index for RAG pages |
| `epi_nodes` | Episodic graph nodes |
| `epi_edges` | Episodic graph edges |
| `temporal_events` | Temporal event storage |
| `temporal_links` | Temporal event links |
| `user_wiki` | User wiki entries |
| `agent_wiki` | Agent wiki entries |
| `user_wiki_fts` | FTS5 index for user wiki |
| `agent_wiki_fts` | FTS5 index for agent wiki |
| `wiki_index` | File-based wiki index |
| `wiki_fts` | FTS5 index for wiki files |
| `memory_conflicts` | Conflict tracking |
| `migration_log` | Migration version log |

---

## ReadOnlyReplica (`shared/read_only.py`)

Read-only SQLite database copy for dashboard and metrics queries. Uses `sqlite3.backup()` for safe hot-copy.

### Class: `ReadOnlyReplica`

```python
class ReadOnlyReplica:
    def __init__(self, source_dir: str = None, replica_dir: str = None)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `source_dir` | `str` | `None` | Source DB directory. Defaults to `~/.mcp-ariel-memory`. |
| `replica_dir` | `str` | `None` | Replica directory. Defaults to `~/.mcp-ariel-memory/replica`. |

### `ReadOnlyReplica.sync`

```python
def sync(self) -> Dict[str, int]
```

Synchronizes the replica from the source. Falls back to `shutil.copy2` if `sqlite3.backup` fails.

**Returns**: Dict mapping filenames to success (1) or failure (0).

```python
from shared.read_only import read_only_replica

result = read_only_replica.sync()
# {"memory.db": 1}
```

### `ReadOnlyReplica.start_auto_sync`

```python
def start_auto_sync(self, interval_seconds: int = 300)
```

Starts a background thread that syncs at the given interval.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `interval_seconds` | `int` | `300` | Sync interval in seconds. |

```python
read_only_replica.start_auto_sync(interval_seconds=60)
```

### `ReadOnlyReplica.stop`

```python
def stop(self)
```

Stops the auto-sync thread.

```python
read_only_replica.stop()
```

### `ReadOnlyReplica.get_conn`

```python
def get_conn(self, db_name: str = "memory.db") -> sqlite3.Connection
```

Returns a read-only connection. Uses `?mode=ro` URI. Falls back to source if replica doesn't exist.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `db_name` | `str` | `"memory.db"` | Database filename. |

**Returns**: `sqlite3.Connection` with `row_factory = sqlite3.Row`.

```python
conn = read_only_replica.get_conn("memory.db")
cursor = conn.execute("SELECT COUNT(*) FROM core_memory WHERE user_id=?", ("alice",))
print(cursor.fetchone()[0])  # 42
```

### `ReadOnlyReplica.is_ready`

```python
def is_ready(self) -> bool
```

**Returns**: `True` if the replica `memory.db` exists.

```python
if read_only_replica.is_ready():
    conn = read_only_replica.get_conn()
```

### Global Instance

```python
from shared.read_only import read_only_replica
```

---

## Security — Envelope Encryption (`features/secrets.py`)

All sensitive data (API keys, bearer tokens, saga state) is encrypted at rest using libsodium secretbox (AES-256-GCM). Legacy plain JSON files are automatically rotated to encrypted format on first read.

### Master Key Resolution

The master key is resolved in order:

1. `crypto.master_key_hex` in `config.yaml`
2. OS keychain via `keyring` library
3. `MCP_MASTER_KEY` environment variable (argon2id KDF)
4. **Fail loud** if none available

### API

```python
from features.secrets import encrypt_json, decrypt_json, is_encrypted_blob

# Encrypt
blob = encrypt_json({"api_key": "ak_abc123"})
# Returns: nonce(24 bytes) || ciphertext

# Decrypt
data = decrypt_json(blob)
# Returns: {"api_key": "ak_abc123"}

# Check if file is encrypted
if is_encrypted_blob(Path("~/.mcp-ariel-memory/api_keys.json")):
    print("File is encrypted")
```

### What's Encrypted

| File | Location | Encrypted |
|------|----------|-----------|
| API keys | `~/.mcp-ariel-memory/api_keys.json` | ✅ Yes |
| Bearer token | `~/.mcp-ariel-memory/bearer_token.json` | ✅ Yes |
| Saga state | `~/.mcp-ariel-memory/sagas/*.json` | ✅ Yes |
| Config | `config.yaml` | ❌ No (settings only) |

### Setup

```bash
# Option 1: Environment variable
export MCP_MASTER_KEY="your-32-byte-hex-key"

# Option 2: config.yaml
crypto:
  master_key_hex: "your-32-byte-hex-key"

# Option 3: OS keychain (recommended for production)
python -c "from features.secrets import install_master_key_to_keychain; install_master_key_to_keychain('your-key')"
```

### Legacy Migration

If you have existing plain JSON files, they are automatically encrypted on first read:

1. System detects plain JSON (starts with `{` or `[`)
2. Reads the data
3. Writes encrypted version
4. Logs deprecation warning

No manual migration needed — just set a master key and restart.

### Dependencies

```bash
pip install pynacl  # Required for encryption
pip install keyring  # Optional: OS keychain support
```
