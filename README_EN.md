# mcp-ariel-memory

**Universal Two-Layer Memory MCP Server**

A two-layer universal memory system for AI agents. Real MCP Python SDK, async, 27 tools, stdio + HTTP transports, dashboard, metrics, authentication, automatic backups, external wiki folders.

---

## Quick Start

```bash
# Install
git clone <repo> && cd mcp-ariel-memory
pip install -e ".[all]"

# Run (stdio — for Claude Desktop)
python -m mcp_ariel_memory --transport stdio

# Run (HTTP — for web clients)
python -m mcp_ariel_memory --transport http --port 8000

# Run (HTTP + Dashboard + Metrics)
python -m mcp_ariel_memory --transport http --port 8000 --dashboard
```

### Docker

```bash
docker build -t ariel-memory .
docker run -p 8000:8000 ariel-memory

# Or docker-compose
docker-compose up
```

### Claude Desktop

Add to `claude_desktop_config.json`:

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

---

## Architecture

### Tech Stack

| Component | Technology |
|-----------|-----------|
| MCP protocol | Python MCP SDK v1.28 (FastMCP) |
| Transports | stdio + Streamable HTTP |
| Storage | SQLite (WAL mode) |
| Search | FTS5 + sqlite-vec (optional) |
| Async | asyncio + to_thread for SQLite |
| Docker | Dockerfile + docker-compose |
| Testing | pytest + pytest-asyncio |
| CI/CD | GitHub Actions |

### Two-Layer Model

```
┌─────────────────────────────────────────────────────┐
│               MCP Server (31 async tools)            │
│  FastMCP + stdio/HTTP transports + auth              │
├──────────────────────┬──────────────────────────────┤
│   Layer 1: User      │   Layer 2: Agent             │
│   User facts         │   Agent identity             │
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
│ Shared: Cache | DB Pool | Embeddings                │
└─────────────────────────────────────────────────────┘
```

### Memory Hierarchy L1 → L4

| Level | Purpose | Storage | Limit |
|-------|---------|---------|-------|
| **L1 ReflexBuffer** | Recent messages (ring buffer) | RAM + JSON | 50 |
| **L2 SessionStore** | Session history with indexes | SQLite | 100 |
| **L3 EpisodicMemory** | Important moments with emotional weight | SQLite | 1000 |
| **L4 CoreMemory** | Key-value facts with importance | SQLite | 5000 |

### Consolidation

```
Message → L1 (buffer)
         → ImportanceGate (noise filter, threshold 0.3)
         → L2 (session)
         → EmotionTrigger (emotional analysis)
         → L3 (episodes, if importance > 0.7)
         → L4 (consolidation, if weight > 0.7)
```

---

## MCP Tools — Full Reference

### User Layer (10 tools)

#### `memory_user_remember`

Save a fact to L4 CoreMemory.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | string | `"default"` | User identifier |
| `key` | string | `""` | Fact key (e.g. `"name"`, `"lang"`) |
| `value` | string | `""` | Value |
| `importance` | float | `0.5` | Importance 0.0–1.0 |

**Response:** `{"status": "ok", "entry_id": 42}`

**Examples:**
```python
# Name
await mcp.call_tool("memory_user_remember", {
    "user_id": "alice", "key": "name", "value": "Alice", "importance": 0.9
})

# Programming language
await mcp.call_tool("memory_user_remember", {
    "user_id": "alice", "key": "primary_language", "value": "Python", "importance": 0.8
})

# Upsert (update existing)
await mcp.call_tool("memory_user_remember", {
    "user_id": "alice", "key": "name", "value": "Alice Smith", "importance": 0.95
})
```

#### `memory_user_recall`

Search user memory (L3 + L4).

**Parameters:** `user_id`, `query`, `limit` (default 10)

**Response:** `{"results": [{"key": "name", "value": "Alice", "importance": 0.9}], "count": 1}`

```python
result = await mcp.call_tool("memory_user_recall", {
    "user_id": "alice", "query": "name"
})
```

#### `memory_user_forget`

Delete a fact from L4.

**Parameters:** `user_id`, `key`

**Response:** `{"deleted": true}` or `{"deleted": false}`

```python
await mcp.call_tool("memory_user_forget", {"user_id": "alice", "key": "hobby"})
```

#### `memory_user_session_start`

Start a new session.

**Response:** `{"session_id": "sess_alice_1782036546_0b6ec91f"}`

#### `memory_user_session_end`

End a session with summary.

**Parameters:** `user_id`, `session_id`, `summary`

#### `memory_user_episode_save`

Save an important episode to L3.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `summary` | string | `""` | Episode description |
| `weight` | float | `0.5` | Emotional weight 0.0–1.0 |
| `tags` | list[str] | `None` | Tags (e.g. `["greeting", "work"]`) |

```python
await mcp.call_tool("memory_user_episode_save", {
    "user_id": "alice", "summary": "User changed jobs",
    "weight": 0.8, "tags": ["work", "life_change"]
})
```

#### `memory_user_episode_recall`

Find episodes (all or by tag).

**Parameters:** `user_id`, `tag` (optional), `limit`

```python
result = await mcp.call_tool("memory_user_episode_recall", {"user_id": "alice", "tag": "work"})
```

#### `memory_user_graph_add`

Add node to epistemic graph.

**Parameters:** `content`, `node_type` (default `"fact"`), `tags`

#### `memory_user_graph_query`

Query graph by tag or type.

**Parameters:** `user_id`, `tag`, `node_type`, `limit`

#### `memory_user_stats`

Memory statistics across all layers.

---

### Agent Layer (10 tools)

Same as user tools but for agent identity.

| Tool | Description |
|------|-------------|
| `memory_agent_remember` | Save decision/error/principle |
| `memory_agent_recall` | Search agent memory |
| `memory_agent_forget` | Delete agent fact |
| `memory_agent_session_start` | Start agent session |
| `memory_agent_session_end` | End agent session |
| `memory_agent_episode_save` | Save agent episode |
| `memory_agent_episode_recall` | Find agent episodes |
| `memory_agent_graph_add` | Add agent graph node |
| `memory_agent_graph_query` | Query agent graph |
| `memory_agent_stats` | Agent statistics |

---

### Auth (3 tools)

| Tool | Parameters | Response |
|------|-----------|----------|
| `memory_create_api_key` | `user_id`, `label` | `{"api_key": "ak_..."}` |
| `memory_revoke_api_key` | `api_key` | `{"revoked": true}` |
| `memory_list_api_keys` | — | `{"keys": [...]}` |

### Backup (4 tools)

| Tool | Parameters | Response |
|------|-----------|----------|
| `memory_backup_now` | — | `{"path": "..."}` |
| `memory_backup_list` | — | `{"backups": [...]}` |
| `memory_backup_restore` | `backup_name` | `{"restored": [...]}` |
| `memory_backup_status` | — | `{"running": true, ...}` |

---

## Modules

### core/ — Memory Core (L1-L4)

```python
from core import memory_manager

user = memory_manager.user_memory("alice")
user.remember("name", "Alice", 0.9)
results = user.recall("name")
user.get_context()

agent = memory_manager.agent_memory("alice")
agent.remember("approach", "YAGNI first", 0.9)
```

### rag/ — Hybrid Search (FTS5 + RRF)

```python
from rag.engine import RAGEngine

rag = RAGEngine(layer="user")
rag.ingest_text("Title", "Content", user_id="alice")

# FTS5 search
results = rag.search("query", user_id="alice")

# RRF — hybrid search (FTS5 + vector similarity)
results = rag.search_rrf("query", user_id="alice", limit=5)
# [{"id": 1, "title": "...", "score": 0.0325, "source": "rrf(fts+vec)"}]
```

**search_rrf** combines FTS5 + vector via Reciprocal Rank Fusion (k=60).

### graph/ — Knowledge Graph

```python
from graph.epistemic import EpistemicGraph
from graph.temporal import TemporalGraph

g = EpistemicGraph(layer="user")
n = g.add_node("alice", "Prefers Python", "fact", ["fact_about_user"])
nodes = g.query_by_tag("alice", "fact_about_user")

tg = TemporalGraph()
e = tg.add_event("alice", "message", "Hello")
timeline = tg.get_timeline("alice")
```

### lifecycle/ — Memory Lifecycle

```python
from lifecycle.forgetting import ForgettingSystem
from lifecycle.emotion_trigger import EmotionTrigger

ForgettingSystem().cleanup()
should, reason, weight = EmotionTrigger().should_save("I love this!")
```

### hooks/ — 24 Hooks

```python
from hooks.registry import HookRegistry
hr = HookRegistry()
hr.register("my_hook", lambda ctx: {"ok": True})
hr.fire("my_hook", "user", {})
```

### shared/ — Saga + Middleware + Cache + Embeddings + Metrics + DreamBuffer + Archive

```python
from shared.saga import Saga, saga_watchdog, create_backup_saga
from shared.middleware import MiddlewarePipeline, MiddlewareContext, ValidationMiddleware
from shared.cache import MemoryCache
from shared.embeddings import EmbeddingCache, embed_text, similarity, DEFAULT_MODEL
from shared.metrics import metrics
from shared.dream_buffer import DreamBuffer
from shared.archived_memories import ArchivedMemories

# Saga — multi-step with persistence + timeout + watchdog
saga = Saga("backup", timeout_seconds=60)
saga.add_step("copy", copy_fn, compensate_fn)
result = await saga.execute()
saga_watchdog.start()  # detect stuck sagas

# Middleware pipeline
pipeline = MiddlewarePipeline()
pipeline.add(ValidationMiddleware())

# Embeddings — multilingual (100+ languages including Russian)
print(DEFAULT_MODEL)  # "intfloat/multilingual-e5-small"
cache = EmbeddingCache()
emb = cache.embed_single("Привет мир")  # Russian works!

# DreamBuffer — staging with TTL (auto-cleanup > 24h or > 500 items)
db = DreamBuffer()
db.add("alice", "sess1", "message", importance=0.6)
db.cleanup_old(max_age_hours=24, max_count=500)

# ArchivedMemories — restorable
am = ArchivedMemories()
am.archive("alice", "Old memory", importance=0.2, reason="inactive_30d")
```

**Saga:** persistence to disk, watchdog (60s interval), timeout per step, compensation on failure

**Middleware:** Validation, RateLimit, ImportanceGate, Audit, Dedup

**AuditTrail rotation:**
```python
from features.audit_trail import AuditTrail
at = AuditTrail()
at.archive_and_prune(retention_days=30)  # archive → JSON → delete
```

### wiki/ — FileWiki (files as source of truth + FTS5 index)

```python
from wiki.file_wiki import FileWiki

uw = FileWiki(layer="user")
aw = FileWiki(layer="agent")

# Write — creates .md file + indexes to FTS5
path = uw.add("diary", "Day 1", "Started project", tags=["work"], importance=0.7)

# Search — FTS5 across all .md files
results = uw.search("project")

# Read
entry = uw.get(path)

# Reindex all .md from disk
uw.reindex_all()
```

**Architecture:** `.md` files on disk = source of truth, `wiki_index.db` (FTS5) = search index.

**File format (YAML frontmatter):**
```markdown
---
title: "Meeting Notes"
tags: work, important
importance: 0.7
updated: 2026-06-21
---
# Meeting Notes
Content here...
```

**Types:** diary, relationships, desires, aspirations, work_notes, preferences, retrospective (user) + decision_log, error_analysis, personality_evolution, emotional_context, wiki_agent, learning_journal, principle_log (agent)

### features/ — Auth, Backup, Dashboard, etc.

```python
from features.auth import APIKeyAuth
from features.backup_cron import backup_cron
from features.dashboard import Dashboard
from shared.metrics import metrics
from shared.embeddings import embed_text
```

---

## Wiki — External Folders and 14 Types

### Enable/Disable Types

```yaml
wiki:
  user:
    diary: true
    relationships: false  # disabled
    external_dirs:
      - "/home/user/notes"
  agent:
    wiki_agent: true
    external_dirs:
      - "/path/to/lore"
```

### File Mapping

| File/Folder | Type |
|-------------|------|
| `lore/world.md` | `wiki_agent` |
| `knowledge/python.md` | `wiki_agent` |
| `style-guide/tone.md` | `personality_evolution` |
| `errors/auth-bug.md` | `error_analysis` |
| `decisions/db-choice.md` | `decision_log` |
| `principles/testing.md` | `principle_log` |

---

## Authentication

### API Keys

```bash
curl -X POST http://localhost:8000/api/auth/create \
  -H "Content-Type: application/json" \
  -d '{"user_id": "alice", "label": "my key"}'
```

### Bearer Token

```bash
curl -H "Authorization: Bearer mt_..." http://localhost:8000/api/stats
```

---

## Backup Cron

```bash
curl -X POST http://localhost:8000/api/backup/trigger
curl http://localhost:8000/api/backup/list
```

---

## Configuration (config.yaml)

```yaml
layers: { user: { enabled: true }, agent: { enabled: true } }
limits: { l1_buffer_size: 50, l4_core_limit: 5000 }
hooks: { user: { message_received: true, ... }, agent: { error_occurred: true, ... } }
forgetting: { decay_rate: 0.01, archive_threshold_days: 90 }
rag: { fts_enabled: true, vec_enabled: true }
embeddings: { model: "BAAI/bge-small-en-v1.5" }
graph: { temporal_enabled: true, epistemic_enabled: true }
wiki:
  user: { diary: true, ..., external_dirs: ["/path/to/notes"] }
  agent: { decision_log: true, ..., external_dirs: ["/path/to/lore"] }
auth: { api_keys_enabled: true, bearer_token_enabled: true }
backup: { auto_backup: true, backup_interval_hours: 24 }
security: { per_user_isolation: true, rate_limit_per_user: 100 }
```

---

## Testing

```bash
python -m pytest tests/ -v
uv run mcp dev mcp_server.py  # MCP Inspector
```

**Status:** 10/10 pytest + 31/31 MCP tools.

---

## Project Structure

```
mcp-ariel-memory/
├── pyproject.toml
├── Dockerfile / docker-compose.yml
├── .github/workflows/ci.yml
├── config.yaml / config.py
├── mcp_server.py              # MCP SDK (31 async tools)
├── server.py                  # Legacy (backward compat)
├── tests/test_all.py
├── core/                      # L1-L4
│   ├── reflex.py, session.py, episodic.py, memory.py
├── rag/                       # Search
│   ├── engine.py, router.py, conflict.py
├── graph/                     # Graph
│   ├── epistemic.py, temporal.py
├── lifecycle/                 # Lifecycle
│   ├── forgetting.py, emotion_trigger.py, consolidation.py
├── hooks/                     # 24 hooks
│   ├── registry.py, user_hooks.py, agent_hooks.py
├── wiki/                      # Wiki (14 types)
│   ├── user_wiki.py, agent_wiki.py
├── features/                  # Features
│   ├── auth.py, backup.py, backup_cron.py, dashboard.py
│   ├── import_export.py, audit_trail.py, compression.py, rate_limiting.py
└── shared/                    # Shared
    ├── cache.py, db_pool.py, embeddings.py, metrics.py
```

**Total:** 50+ files, 31 MCP tools (async, MCP SDK), 24 hooks, 14 wiki types, external folders, RRF, saga+watchdog, middleware, dashboard+auth, metrics, backup cron, DreamBuffer TTL, AuditTrail rotation, memory_cleanup, Docker, CI/CD, pytest.
