# Knowledge Graph — `graph/`

Async, layer-aware epistemic graph and temporal graph backed by SQLite with WAL journal mode.

```python
from graph import EpistemicGraph, TemporalGraph
```

---

## EpistemicGraph (`graph/epistemic.py`)

Layer-aware epistemic graph with CTE `WITH RECURSIVE` for BFS traversal in SQLite.

### Constructor

```python
EpistemicGraph(cm=None, layer: str = "user")
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cm` | `AsyncConnectionManager` | `None` (uses global `connection_manager`) | Database connection manager |
| `layer` | `str` | `"user"` | Graph layer — `"user"` or `"agent"` |

```python
g_user = EpistemicGraph(layer="user")
g_agent = EpistemicGraph(layer="agent")
```

### `init_db()`

```python
async def init_db(self) -> None
```

Creates `epi_nodes`, `epi_edges`, and `epi_tags` tables with indexes. Runs automatically on first use. Handles migration (adds `layer` column if missing from older databases).

Tags are stored in a separate `epi_tags` table for fast indexed lookups (migration v3).

```python
await g.init_db()
```

### `add_node()`

```python
async def add_node(self, user_id: str, content: str, node_type: str,
                   tags: List[str] = None, confidence: float = 0.5) -> int
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | required | Owner of the node |
| `content` | `str` | required | Node text content |
| `node_type` | `str` | required | Category (e.g. `"fact"`, `"decision"`, `"error_analysis"`) |
| `tags` | `List[str]` | `None` | List of tag strings |
| `confidence` | `float` | `0.5` | Confidence score (0.0–1.0) |

**Returns**: `int` — the new node's `node_id`.

```python
n1 = await g.add_node("alice", "Prefers Python over JavaScript", "fact",
                       ["fact_about_user", "user_preference"], 0.9)
# n1 = 1
```

### `add_edge()`

```python
async def add_edge(self, source_id: int, target_id: int, relation: str,
                   weight: float = 0.8) -> None
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `source_id` | `int` | required | Source node ID |
| `target_id` | `int` | required | Target node ID |
| `relation` | `str` | required | Edge label (e.g. `"related_to"`, `"corrected_by"`) |
| `weight` | `float` | `0.8` | Edge weight (0.0–1.0) |

Upserts — overwrites existing edge with same `(source_id, target_id, relation)`.

```python
await g.add_edge(n1, n2, "related_to", 0.8)
```

### `query_by_tag()`

```python
async def query_by_tag(self, user_id: str, tag: str, limit: int = 20) -> List[EpistemicNode]
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | required | Filter by owner |
| `tag` | `str` | required | Tag to match (uses epi_tags table with JOIN) |
| `limit` | `int` | `20` | Max results |

**Returns**: `List[EpistemicNode]` — sorted by confidence descending.

```python
nodes = await g.query_by_tag("alice", "fact_about_user")
# [EpistemicNode(node_id=1, user_id="alice", layer="user", content="Prefers Python...",
#   node_type="fact", tags=["fact_about_user", "user_preference"], confidence=0.9, ...)]
```

### `query_by_type()`

```python
async def query_by_type(self, user_id: str, node_type: str, limit: int = 20) -> List[EpistemicNode]
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | required | Filter by owner |
| `node_type` | `str` | required | Node type to match exactly |
| `limit` | `int` | `20` | Max results |

**Returns**: `List[EpistemicNode]` — sorted by confidence descending.

```python
decisions = await g.query_by_type("alice", "decision")
# [EpistemicNode(node_id=5, user_id="alice", ..., node_type="decision", ...)]
```

### `get_neighbors()`

```python
async def get_neighbors(self, node_id: int, depth: int = 1) -> List[Dict[str, Any]]
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `node_id` | `int` | required | Starting node |
| `depth` | `int` | `1` | BFS depth (1 = immediate neighbors only) |

**Returns**: `List[Dict]` — each dict has keys `id`, `content`, `type`, `tags`, `relation`, `weight`.

Uses a recursive CTE — works in SQLite without external graph databases.

```python
neighbors = await g.get_neighbors(n1, depth=2)
# [{"id": 2, "content": "Knows JavaScript", "type": "fact",
#   "tags": ["fact_about_user"], "relation": "related_to", "weight": 0.8}]
```

**SQL (recursive CTE):**
```sql
WITH RECURSIVE graph AS (
    SELECT e.source_id, e.target_id, e.relation, e.weight, 1 as d
    FROM epi_edges e WHERE e.source_id = ?
    UNION ALL
    SELECT e.source_id, e.target_id, e.relation, e.weight, g.d + 1
    FROM epi_edges e JOIN graph g ON e.source_id = g.target_id
    WHERE g.d < ?
)
SELECT n.node_id, n.content, n.node_type, n.tags, g.relation, g.weight
FROM graph g JOIN epi_nodes n ON g.target_id = n.node_id
WHERE n.layer = ?
```

### `find_path()`

```python
async def find_path(self, source_id: int, target_id: int,
                    max_depth: int = None) -> List[Dict[str, Any]]
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `source_id` | `int` | required | Start node |
| `target_id` | `int` | required | End node |
| `max_depth` | `int` | `None` (falls back to `config.graph.max_depth`, default 3) | Max search depth |

**Returns**: `List[Dict]` — each dict has keys `target`, `relation`, `weight`, `depth`.

```python
path = await g.find_path(n1, n2, max_depth=3)
# [{"target": 2, "relation": "related_to", "weight": 0.8, "depth": 1}]

# Uses config default when max_depth not specified
path = await g.find_path(n1, n2)
```

### `count_nodes()`

```python
async def count_nodes(self, user_id: str = None) -> int
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | `None` | If provided, count only that user's nodes |

**Returns**: `int` — total node count in the layer.

```python
total = await g.count_nodes()
alice_count = await g.count_nodes("alice")
```

### `_row_to_node()`

```python
def _row_to_node(self, row) -> EpistemicNode
```

Private helper — converts a database row dict to an `EpistemicNode` dataclass.

---

### EpistemicNode dataclass

```python
@dataclass
class EpistemicNode:
    node_id: int
    user_id: str
    layer: str
    content: str
    node_type: str
    tags: List[str]
    confidence: float
    created_at: float
```

### Tag Constants

#### User Layer (`USER_TAGS`)

| Key | Display Name |
|-----|--------------|
| `fact_about_user` | Fact about user |
| `user_decision` | User decision |
| `user_preference` | User preference |
| `user_emotion` | User emotion |

#### Agent Layer (`AGENT_TAGS`)

| Key | Display Name |
|-----|--------------|
| `learned_from` | Learned from error |
| `decided_because` | Agent decision |
| `evolved_to` | Personality evolved |
| `felt_in_context` | Emotion in context |
| `wiki_contains` | Second brain |
| `error_pattern` | Error pattern |
| `correction_pattern` | Correction pattern |
| `personality_trait` | Personality trait |

---

## TemporalGraph (`graph/temporal.py`)

Temporal graph for time-based memory: events, timelines, and causal chains.

### Constructor

```python
TemporalGraph(cm=None)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cm` | `AsyncConnectionManager` | `None` (uses global `connection_manager`) | Database connection manager |

```python
tg = TemporalGraph()
```

### `init_db()`

```python
async def init_db(self) -> None
```

Creates `temporal_events` and `temporal_links` tables with indexes.

```python
await tg.init_db()
```

### `add_event()`

```python
async def add_event(self, user_id: str, event_type: str, content: str,
                    importance: float = 0.5, metadata: Dict = None) -> int
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | required | Owner of the event |
| `event_type` | `str` | required | Category (e.g. `"message"`, `"response"`, `"tool_call"`) |
| `content` | `str` | required | Event text content |
| `importance` | `float` | `0.5` | Importance score (0.0–1.0) |
| `metadata` | `Dict` | `None` | Arbitrary JSON metadata |

**Returns**: `int` — the new event's `event_id`. Timestamp is set to `time.time()` automatically.

```python
e1 = await tg.add_event("alice", "message", "I need help with auth", importance=0.6)
e2 = await tg.add_event("alice", "response", "Here's how to fix it", importance=0.5)
```

### `link_events()`

```python
async def link_events(self, from_event: int, to_event: int,
                      link_type: str = "follows", strength: float = 0.5) -> None
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `from_event` | `int` | required | Source event ID |
| `to_event` | `int` | required | Target event ID |
| `link_type` | `str` | `"follows"` | Relation type (e.g. `"follows"`, `"caused_by"`) |
| `strength` | `float` | `0.5` | Link strength (0.0–1.0) |

Upserts — overwrites existing link with same `(from_event, to_event, link_type)`.

```python
await tg.link_events(e1, e2, "follows", 0.7)
```

### `get_timeline()`

```python
async def get_timeline(self, user_id: str, limit: int = 50,
                       offset: int = 0) -> List[TemporalEvent]
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | required | Filter by owner |
| `limit` | `int` | `50` | Max results |
| `offset` | `int` | `0` | Pagination offset |

**Returns**: `List[TemporalEvent]` — most recent first (ordered by `timestamp DESC`).

```python
timeline = await tg.get_timeline("alice", limit=10)
# [TemporalEvent(event_id=2, user_id="alice", event_type="response",
#   content="Here's how", timestamp=1719..., importance=0.5, metadata={}), ...]

# Paginate
page2 = await tg.get_timeline("alice", limit=50, offset=50)
```

### `get_events_near()`

```python
async def get_events_near(self, user_id: str, timestamp: float,
                          window_seconds: float = 3600,
                          limit: int = 20) -> List[TemporalEvent]
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | required | Filter by owner |
| `timestamp` | `float` | required | Center timestamp (Unix epoch) |
| `window_seconds` | `float` | `3600` | Half-window in seconds (default ±1 hour) |
| `limit` | `int` | `20` | Max results |

**Returns**: `List[TemporalEvent]` — events within `window_seconds` of `timestamp`, ordered by timestamp ascending.

```python
import time

# Events from the last hour
recent = await tg.get_events_near("alice", time.time(), window_seconds=3600)

# Events within 30 minutes of a specific time
specific = await tg.get_events_near("alice", 1719500000.0, window_seconds=1800)
```

### `get_causal_chain()`

```python
async def get_causal_chain(self, event_id: int, direction: str = "forward",
                           limit: int = 10) -> List[Dict[str, Any]]
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `event_id` | `int` | required | Starting event |
| `direction` | `str` | `"forward"` | `"forward"` = events that follow, `"backward"` = events that preceded |
| `limit` | `int` | `10` | Max results |

**Returns**: `List[Dict]` — each dict has keys `event_id`, `type`, `content`, `timestamp`.

```python
# What happened after e1?
chain = await tg.get_causal_chain(e1, direction="forward", limit=5)
# [{"event_id": 2, "type": "response", "content": "Here's how", "timestamp": 1719...}]

# What led to e2?
causes = await tg.get_causal_chain(e2, direction="backward", limit=5)
# [{"event_id": 1, "type": "message", "content": "I need help", "timestamp": 1719...}]
```

### `count_events()`

```python
async def count_events(self, user_id: str = None) -> int
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | `None` | If provided, count only that user's events |

**Returns**: `int` — total event count.

```python
total = await tg.count_events()
alice_count = await tg.count_events("alice")
```

---

### TemporalEvent dataclass

```python
@dataclass
class TemporalEvent:
    event_id: int
    user_id: str
    event_type: str
    content: str
    timestamp: float
    importance: float
    metadata: Dict
```

---

## Database Schema

### `epi_nodes`

| Column | Type | Notes |
|--------|------|-------|
| `node_id` | `INTEGER` | Primary key, autoincrement |
| `layer` | `TEXT` | `"user"` or `"agent"` |
| `user_id` | `TEXT` | Owner |
| `content` | `TEXT` | Node text |
| `node_type` | `TEXT` | Category |
| `tags` | `TEXT` | JSON array of strings |
| `confidence` | `REAL` | Default `0.5` |
| `created_at` | `REAL` | Unix timestamp |

### `epi_edges`

| Column | Type | Notes |
|--------|------|-------|
| `source_id` | `INTEGER` | FK → `epi_nodes.node_id` |
| `target_id` | `INTEGER` | FK → `epi_nodes.node_id` |
| `relation` | `TEXT` | Edge label |
| `weight` | `REAL` | Default `0.8` |
| `created_at` | `REAL` | Unix timestamp |

Primary key: `(source_id, target_id, relation)`

### `temporal_events`

| Column | Type | Notes |
|--------|------|-------|
| `event_id` | `INTEGER` | Primary key, autoincrement |
| `user_id` | `TEXT` | Owner |
| `event_type` | `TEXT` | Category |
| `content` | `TEXT` | Event text |
| `timestamp` | `REAL` | Unix timestamp |
| `importance` | `REAL` | Default `0.5` |
| `metadata` | `TEXT` | JSON object |

### `temporal_links`

| Column | Type | Notes |
|--------|------|-------|
| `from_event` | `INTEGER` | FK → `temporal_events.event_id` |
| `to_event` | `INTEGER` | FK → `temporal_events.event_id` |
| `link_type` | `TEXT` | Default `"follows"` |
| `strength` | `REAL` | Default `0.5` |

Primary key: `(from_event, to_event, link_type)`

---

## WAL Journal Mode

All SQLite connections use Write-Ahead Logging for concurrent reads:

```python
# Configured automatically in AsyncConnectionManager:
# PRAGMA journal_mode=WAL
# PRAGMA busy_timeout=5000
# PRAGMA synchronous=NORMAL
```

---

## Full Example

```python
import asyncio
import time
from graph import EpistemicGraph, TemporalGraph

async def main():
    # --- Epistemic layer ---
    g = EpistemicGraph(layer="user")
    await g.init_db()

    n1 = await g.add_node("alice", "Prefers Python", "fact", ["fact_about_user"], 0.9)
    n2 = await g.add_node("alice", "Knows JavaScript", "fact", ["fact_about_user"], 0.7)
    n3 = await g.add_node("alice", "Chose SQLite", "decision", ["user_decision"], 0.8)
    await g.add_edge(n1, n2, "related_to", 0.8)
    await g.add_edge(n2, n3, "influenced_by", 0.6)

    # Query
    facts = await g.query_by_tag("alice", "fact_about_user")
    neighbors = await g.get_neighbors(n1, depth=2)
    path = await g.find_path(n1, n3, max_depth=3)
    total = await g.count_nodes("alice")

    # --- Temporal layer ---
    tg = TemporalGraph()
    await tg.init_db()

    e1 = await tg.add_event("alice", "message", "Help with auth", importance=0.6)
    e2 = await tg.add_event("alice", "response", "Use JWT tokens", importance=0.7)
    e3 = await tg.add_event("alice", "followup", "Thanks, it worked", importance=0.4)
    await tg.link_events(e1, e2, "follows")
    await tg.link_events(e2, e3, "follows")

    timeline = await tg.get_timeline("alice", limit=10)
    recent = await tg.get_events_near("alice", time.time(), window_seconds=7200)
    chain = await tg.get_causal_chain(e1, direction="forward")
    total_events = await tg.count_events("alice")

asyncio.run(main())
```
