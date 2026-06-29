# Memory Core — `core/` (async)

The core module implements a four-layer memory architecture:
- **L1** `ReflexBuffer` — ring buffer for recent messages (RAM + JSON persistence)
- **L2** `SessionStore` — async session history with SQLite
- **L3** `EpisodicMemory` — important moments with emotional weight
- **L4** `CoreMemory` — key-value facts with importance scoring

---

## ReflexEntry (`core/reflex.py`)

```python
@dataclass
class ReflexEntry:
    role: str          # "user" or "assistant"
    content: str       # message text
    tokens: int        # token count estimate
    timestamp: float   # Unix timestamp
```

---

## L1 ReflexBuffer (`core/reflex.py`)

Circular buffer for recent messages. Thread-safe. Optional JSON persistence.

### `__init__(max_size=50, persist_path=None)`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_size` | `int` | `50` | Maximum entries in buffer |
| `persist_path` | `str` | `None` | File path for JSON persistence. `None` = RAM only |

```python
from core.reflex import ReflexBuffer

buf = ReflexBuffer(max_size=50, persist_path="reflex.json")
```

### `add(role, content, tokens=0)`

Add a message to the buffer. Creates a `ReflexEntry` with current timestamp.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `role` | `str` | — | `"user"` or `"assistant"` |
| `content` | `str` | — | Message text |
| `tokens` | `int` | `0` | Token count estimate |

```python
buf.add(role="user", content="Hello, how are you?", tokens=5)
buf.add(role="assistant", content="I'm doing well!", tokens=4)
```

### `get_recent(n=10) -> List[ReflexEntry]`

Return the last `n` entries from the buffer.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `n` | `int` | `10` | Number of recent entries to return |

```python
recent = buf.get_recent(5)
for entry in recent:
    print(f"{entry.role}: {entry.content}")
```

### `get_full() -> List[ReflexEntry]`

Return all entries currently in the buffer (up to `max_size`).

```python
all_entries = buf.get_full()
print(f"Buffer has {len(all_entries)} entries")
```

### `clear()`

Remove all entries from the buffer. Saves to disk if persistence is enabled.

```python
buf.clear()
assert buf.size() == 0
```

### `size() -> int`

Return the current number of entries in the buffer.

```python
count = buf.size()
```

### `to_text(max_entries=10) -> str`

Format recent entries as text (role: content, truncated to 100 chars each).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_entries` | `int` | `10` | Max entries to format |

```python
text = buf.to_text(max_entries=5)
# Output:
# user: Hello, how are you?
# assistant: I'm doing well!
```

---

## SessionRecord (`core/session.py`)

```python
@dataclass
class SessionRecord:
    session_id: str
    user_id: str
    summary: str
    state_deltas: Dict = field(default_factory=dict)
    topics: List[str] = field(default_factory=list)
    message_count: int = 0
    started_at: float = 0.0
    ended_at: float = 0.0
```

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | `str` | Unique session identifier (`sess_{user_id}_{timestamp}_{uuid}`) |
| `user_id` | `str` | User identifier |
| `summary` | `str` | Session summary text |
| `state_deltas` | `Dict` | State changes during session (JSON serialized) |
| `topics` | `List[str]` | Topics discussed (JSON serialized) |
| `message_count` | `int` | Number of messages in session |
| `started_at` | `float` | Session start timestamp |
| `ended_at` | `float` | Session end timestamp (`0.0` if still active) |

---

## L2 SessionStore (`core/session.py`)

Async session storage with SQLite. Indexes on `user_id` and `started_at`.

### `__init__(cm=None)`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cm` | `AsyncConnectionManager` | `None` | Connection manager. Uses global `connection_manager` if `None` |

```python
from core.session import SessionStore
ss = SessionStore()
```

### `async create_session(user_id) -> str`

Create a new session. Returns the generated session ID.

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | `str` | User identifier |

```python
session_id = await ss.create_session(user_id="alice")
# Returns: "sess_alice_1686000000_a1b2c3d4"
```

### `async close_session(session_id, summary="", state_deltas=None, topics=None)`

Close a session with optional summary and metadata.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `session_id` | `str` | — | Session to close |
| `summary` | `str` | `""` | Session summary |
| `state_deltas` | `Dict` | `None` | State changes during session |
| `topics` | `List[str]` | `None` | Topics discussed |

```python
await ss.close_session(
    session_id,
    summary="Discussed the project architecture",
    state_deltas={"focus": "backend"},
    topics=["architecture", "database"]
)
```

### `async get_recent_sessions(user_id, limit=10) -> List[SessionRecord]`

Get recent sessions for a user, ordered by start time (newest first).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | — | User identifier |
| `limit` | `int` | `10` | Max sessions to return |

```python
sessions = await ss.get_recent_sessions("alice", limit=5)
for s in sessions:
    print(f"{s.session_id}: {s.summary}")
```

### `async get_session_summary(user_id) -> str`

Get a formatted summary of the last 3 sessions for a user.

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | `str` | User identifier |

```python
summary = await ss.get_session_summary("alice")
# Returns:
# - Discussed the project architecture
# - Reviewed code changes
# - Initial setup meeting
```

### `async count_sessions(user_id=None) -> int`

Count sessions. Optionally filter by user.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | `None` | Filter by user. `None` = all users |

```python
user_count = await ss.count_sessions("alice")
total_count = await ss.count_sessions()
```

---

## Episode (`core/episodic.py`)

```python
@dataclass
class Episode:
    episode_id: int
    user_id: str
    summary: str
    emotional_weight: float
    tags: List[str]
    created_at: float
```

| Field | Type | Description |
|-------|------|-------------|
| `episode_id` | `int` | Auto-incrementing primary key |
| `user_id` | `str` | User identifier |
| `summary` | `str` | Episode summary text |
| `emotional_weight` | `float` | Importance/emotional weight (0.0 - 1.0) |
| `tags` | `List[str]` | Tags for categorization (JSON serialized) |
| `created_at` | `float` | Creation timestamp |

---

## L3 EpisodicMemory (`core/episodic.py`)

Async episodic memory with emotional weighting and tag-based search.

### `__init__(cm=None)`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cm` | `AsyncConnectionManager` | `None` | Connection manager. Uses global if `None` |

```python
from core.episodic import EpisodicMemory
ep = EpisodicMemory()
```

### `async save(user_id, summary, emotional_weight=0.5, tags=None) -> int`

Save a new episode. Returns the episode ID.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | — | User identifier |
| `summary` | `str` | — | Episode summary |
| `emotional_weight` | `float` | `0.5` | Importance weight (0.0 - 1.0) |
| `tags` | `List[str]` | `None` | Categorization tags |

```python
episode_id = await ep.save(
    user_id="alice",
    summary="Had a breakthrough with the new algorithm",
    emotional_weight=0.9,
    tags=["breakthrough", "algorithm", "work"]
)
```

### `async get_episodes(user_id, limit=20, offset=0) -> List[Episode]`

Get episodes for a user with pagination support.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | — | User identifier |
| `limit` | `int` | `20` | Max episodes to return |
| `offset` | `int` | `0` | Offset for pagination |

```python
# First page
episodes = await ep.get_episodes("alice", limit=10)

# Second page
episodes = await ep.get_episodes("alice", limit=10, offset=10)
```

### `async search_by_tag(user_id, tag, limit=10) -> List[Episode]`

Search episodes by exact tag match.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | — | User identifier |
| `tag` | `str` | — | Tag to search for |
| `limit` | `int` | `10` | Max results |

```python
work_episodes = await ep.search_by_tag("alice", "work")
breakthrough_episodes = await ep.search_by_tag("alice", "breakthrough")
```

### `async search(user_id, query, limit=10) -> List[Episode]`

Search episodes by text in summary (SQL LIKE, case-insensitive).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | — | User identifier |
| `query` | `str` | — | Text to search for in summary |
| `limit` | `int` | `10` | Max results |

```python
results = await ep.search("alice", "algorithm")
# Returns episodes where summary contains "algorithm"

results = await ep.search("alice", "meeting")
# Returns episodes about meetings
```

### `async archive_old(user_id, days=90) -> int`

Archive old episodes with low emotional weight. Moves to `ArchivedMemories` then deletes.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | — | User identifier |
| `days` | `int` | `90` | Archive episodes older than this many days |

**Archive criteria**: `created_at < cutoff` AND `emotional_weight < 0.3`

```python
archived_count = await ep.archive_old("alice", days=90)
print(f"Archived {archived_count} old episodes")
```

---

## CoreEntry (`core/memory.py`)

```python
@dataclass
class CoreEntry:
    entry_id: int
    user_id: str
    key: str
    value: str
    importance: float
    created_at: float
    updated_at: float
```

| Field | Type | Description |
|-------|------|-------------|
| `entry_id` | `int` | Auto-incrementing primary key |
| `user_id` | `str` | User identifier |
| `key` | `str` | Fact key (unique per user) |
| `value` | `str` | Fact value |
| `importance` | `float` | Importance score (0.0 - 1.0) |
| `created_at` | `float` | Creation timestamp |
| `updated_at` | `float` | Last update timestamp |

---

## L4 CoreMemory (`core/memory.py`)

Async key-value fact storage with importance scoring. Uses UPSERT logic in `save()`.

### `__init__(cm=None)`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cm` | `AsyncConnectionManager` | `None` | Connection manager. Uses global if `None` |

```python
from core.memory import CoreMemory
cm = CoreMemory()
```

### `async save(user_id, key, value, importance=0.5, memory_kind=None, expires_at=None, source="manual", metadata=None) -> int`

Save or update a fact. **UPSERT**: if key exists for user, updates value and importance; otherwise inserts new entry.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | — | User identifier |
| `key` | `str` | — | Fact key (unique per user) |
| `value` | `str` | — | Fact value |
| `importance` | `float` | `0.5` | Importance score (0.0 - 1.0). Auto-filled from type policy if None |
| `memory_kind` | `str` | `None` | Type category. Auto-classified from text if None |
| `expires_at` | `float` | `None` | Expiration timestamp. Required for goal/todo/commitment types |
| `source` | `str` | `"manual"` | Source of the memory (e.g., "manual", "staging_promotion", "episode_promotion") |
| `metadata` | `dict` | `None` | Additional metadata as JSON |

**Typed Memory Categories:**

| Type | Default Importance | Decay Rate | Never Archive | Requires Expires |
|------|-------------------|------------|---------------|------------------|
| `instruction` | 0.9 | 0.0 | Yes | No |
| `fact` | 0.5 | 0.01 | No | No |
| `decision` | 0.7 | 0.005 | No | No |
| `goal` | 0.8 | 0.005 | No | Yes |
| `preference` | 0.7 | 0.003 | No | No |
| `commitment` | 0.85 | 0.0 | Yes | Yes |
| `relationship` | 0.6 | 0.002 | No | No |
| `observation` | 0.4 | 0.02 | No | No |
| `rule` | 0.85 | 0.0 | Yes | No |
| `todo` | 0.6 | 0.005 | No | Yes |
| `question` | 0.5 | 0.05 | No | No |
| `hypothesis` | 0.45 | 0.03 | No | No |
| `context` | 0.3 | 0.05 | No | No |

```python
# Insert new fact
entry_id = await cm.save("alice", "name", "Alice", importance=0.9)

# Insert with type
entry_id = await cm.save("alice", "rule", "Never delete backups",
                         memory_kind="rule", importance=0.85)

# Update existing fact (upsert)
entry_id = await cm.save("alice", "name", "Alice Smith", importance=0.95)

# Auto-classification from text
entry_id = await cm.save("alice", "goal", "Learn Rust by December",
                         memory_kind=None)  # Auto-detects "goal" from keywords
```

### `async list_by_kind(user_id, memory_kind, min_importance=0.0, limit=50) -> list[dict]`

List memories filtered by type.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | — | User identifier |
| `memory_kind` | `str` | — | Type to filter by |
| `min_importance` | `float` | `0.0` | Minimum importance threshold |
| `limit` | `int` | `50` | Maximum results |

```python
rules = await cm.list_by_kind("alice", "rule", min_importance=0.5)
# [{"key": "rule", "value": "Never delete backups", "importance": 0.85, ...}]
```

### `async get(user_id, key) -> Optional[CoreEntry]`

Get a fact by key. Returns `None` if not found.

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | `str` | User identifier |
| `key` | `str` | Fact key |

```python
entry = await cm.get("alice", "name")
if entry:
    print(f"Name: {entry.value}")
else:
    print("Fact not found")
```

### `async get_or_default(user_id, key, default="") -> str`

Get a fact value or return default. **Never returns `None`**.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | — | User identifier |
| `key` | `str` | — | Fact key |
| `default` | `str` | `""` | Default value if not found |

```python
name = await cm.get_or_default("alice", "name", default="unknown")
# Returns "Alice" if exists, otherwise "unknown"
```

### `async get_all(user_id, limit=50) -> List[CoreEntry]`

Get all facts for a user, ordered by importance (highest first).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | — | User identifier |
| `limit` | `int` | `50` | Max entries to return |

```python
all_facts = await cm.get_all("alice")
for entry in all_facts:
    print(f"{entry.key}={entry.value} (importance: {entry.importance})")
```

### `async delete(user_id, key) -> bool`

Delete a fact by key. Returns `True` if deleted, `False` if not found.

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | `str` | User identifier |
| `key` | `str` | Fact key |

```python
deleted = await cm.delete("alice", "old_key")
```

### `async search(user_id, query, limit=10) -> List[Dict]`

Search facts by text in key or value (SQL LIKE, case-insensitive).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | — | User identifier |
| `query` | `str` | — | Text to search for |
| `limit` | `int` | `10` | Max results |

```python
results = await cm.search("alice", "Python")
# Returns: [{"key": "language", "value": "Python", "importance": 0.8}, ...]
```

### `async count(user_id=None) -> int`

Count facts. Optionally filter by user.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | `None` | Filter by user. `None` = all users |

```python
user_count = await cm.count("alice")
total_count = await cm.count()
```

---

## MemoryLayer (`core/__init__.py`)

Unified async memory layer that combines all four memory levels. Used for both user and agent memory.

### `__init__(layer_type, user_id="default", cm=None, cache=None)`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `layer_type` | `str` | — | `"user"` or `"agent"` |
| `user_id` | `str` | `"default"` | User identifier |
| `cm` | `AsyncConnectionManager` | `None` | Connection manager |
| `cache` | `Any` | `None` | Optional cache implementation |

```python
from core import MemoryLayer

user_layer = MemoryLayer("user", user_id="alice")
agent_layer = MemoryLayer("agent", user_id="alice")
```

**Internal layers:**
- `self.l1` — `ReflexBuffer`
- `self.l2` — `SessionStore`
- `self.l3` — `EpisodicMemory`
- `self.l4` — `CoreMemory`

### `async remember(key, value, importance=0.5) -> int`

Save a fact to L4 CoreMemory.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | — | Fact key |
| `value` | `str` | — | Fact value |
| `importance` | `float` | `0.5` | Importance score |

```python
await user_layer.remember("name", "Alice", importance=0.9)
```

### `async recall(query, limit=10) -> List[Dict]`

Search across L4 CoreMemory and L3 EpisodicMemory. Results are cached if cache is configured.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | — | Search query |
| `limit` | `int` | `10` | Max results |

```python
results = await user_layer.recall("Python")
# Returns: [{"key": "language", "value": "Python", "importance": 0.8},
#           {"summary": "Learned Python basics", "weight": 0.7}]
```

### `async forget(key) -> bool`

Delete a fact from L4 CoreMemory.

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `str` | Fact key to delete |

```python
deleted = await user_layer.forget("old_key")
```

### `async get_context() -> str`

Get formatted context string for LLM prompt injection.

**Output format:**
```
RECENT: user: Hello; assistant: Hi there!
FACTS: name=Alice; language=Python
```

- **RECENT**: Last 5 messages from L1 ReflexBuffer (50 chars each)
- **FACTS**: Top 10 facts from L4 CoreMemory (30 chars each, sorted by importance)

```python
context = await user_layer.get_context()
print(context)

# Use in LLM prompt
prompt = f"""
You are an AI assistant.

User context:
{context}

Question: {user_message}
"""
```

### `async cleanup() -> Dict`

Archive old episodes from L3 EpisodicMemory.

```python
result = await user_layer.cleanup()
# Returns: {"archived": 5}
```

---

## MemoryManager (`core/__init__.py`)

Factory for creating and managing `MemoryLayer` instances. Caches layers by type and user.

### `__init__(cm=None, cache=None)`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cm` | `AsyncConnectionManager` | `None` | Connection manager |
| `cache` | `Any` | `None` | Optional cache implementation |

```python
from core import MemoryManager

manager = MemoryManager()
```

### `get_layer(layer_type, user_id="default") -> MemoryLayer`

Get or create a `MemoryLayer` by type and user ID. Layers are cached.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `layer_type` | `str` | — | `"user"` or `"agent"` |
| `user_id` | `str` | `"default"` | User identifier |

```python
layer = manager.get_layer("user", "alice")
```

### `user_memory(user_id="default") -> MemoryLayer`

Convenience method to get a user memory layer.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | `"default"` | User identifier |

```python
user_mem = manager.user_memory("alice")
await user_mem.remember("name", "Alice")
```

### `agent_memory(user_id="default") -> MemoryLayer`

Convenience method to get an agent memory layer.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | `"default"` | User identifier |

```python
agent_mem = manager.agent_memory("alice")
await agent_mem.remember("approach", "YAGNI first", importance=0.9)
```

### `async cleanup_all() -> Dict`

Archive old episodes across all cached layers.

```python
results = await manager.cleanup_all()
# Returns: {"user:alice": {"archived": 3}, "agent:alice": {"archived": 2}}
```

---

## Global Instance

A pre-configured `MemoryManager` is available as `memory_manager`:

```python
from core import memory_manager

# User memory
user_mem = memory_manager.user_memory("alice")
await user_mem.remember("name", "Alice", 0.9)
results = await user_mem.recall("name")
context = await user_mem.get_context()

# Agent memory
agent_mem = memory_manager.agent_memory("alice")
await agent_mem.remember("approach", "YAGNI first", 0.9)

# Cleanup all
await memory_manager.cleanup_all()
```
