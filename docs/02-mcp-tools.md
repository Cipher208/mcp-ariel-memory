# MCP Tools — Full Reference (19 tools)

All layer tools accept a `layer` parameter: `"user"` or `"agent"`.

## Rate Limiting

Write operations are rate-limited per user (default: 100 requests/minute). Read operations are not rate-limited.

When limit exceeded, tools return:
```json
{"error": "rate_limit_exceeded", "remaining": 0, "reset_in": 45}
```

Configure in `config.yaml`:
```yaml
security:
  rate_limit_per_user: 100
```

---

## Layer Tools (11 tools)

### `memory_remember`

Save a fact to L4 CoreMemory.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `layer` | string | `"user"` | `"user"` or `"agent"` |
| `user_id` | string | `"default"` | User identifier |
| `key` | string | `""` | Fact key (e.g. `"name"`, `"principle"`) |
| `value` | string | `""` | Value |
| `importance` | float | `0.5` | Importance 0.0–1.0 |

**Response:** `{"status": "ok", "entry_id": 42}`

```python
# User fact
await mcp.call_tool("memory_remember", {
    "layer": "user", "user_id": "alice",
    "key": "name", "value": "Alice", "importance": 0.9
})

# Agent principle
await mcp.call_tool("memory_remember", {
    "layer": "agent", "user_id": "main",
    "key": "principle", "value": "YAGNI", "importance": 0.9
})
```

### `memory_recall`

Search memory across L3 (episodes) and L4 (facts).

**Parameters:** `layer`, `user_id`, `query`, `limit` (default 10)

**Response:** `{"results": [{"key": "name", "value": "Alice", "importance": 0.9}], "count": 1}`

```python
result = await mcp.call_tool("memory_recall", {
    "layer": "user", "user_id": "alice", "query": "name"
})
```

### `memory_forget`

Delete a fact from L4.

**Parameters:** `layer`, `user_id`, `key`

**Response:** `{"deleted": true}` or `{"deleted": false}`

```python
await mcp.call_tool("memory_forget", {"layer": "user", "user_id": "alice", "key": "hobby"})
```

### `memory_session_start`

Start a new session.

**Parameters:** `layer`, `user_id`

**Response:** `{"session_id": "sess_alice_1782036546_0b6ec91f"}`

### `memory_session_end`

End a session with summary.

**Parameters:** `layer`, `user_id`, `session_id`, `summary`

### `memory_episode_save`

Save an important episode to L3.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `layer` | string | `"user"` | `"user"` or `"agent"` |
| `summary` | string | `""` | Episode description |
| `weight` | float | `0.5` | Emotional weight 0.0–1.0 |
| `tags` | list[str] | `None` | Tags (e.g. `["greeting", "decision"]`) |

```python
await mcp.call_tool("memory_episode_save", {
    "layer": "user", "user_id": "alice",
    "summary": "User changed jobs", "weight": 0.8, "tags": ["work"]
})
```

### `memory_episode_recall`

Find episodes (all or by tag).

**Parameters:** `layer`, `user_id`, `tag` (optional), `limit`

```python
result = await mcp.call_tool("memory_episode_recall", {
    "layer": "user", "user_id": "alice", "tag": "work"
})
```

### `memory_graph_add`

Add node to epistemic graph.

**Parameters:** `layer`, `user_id`, `content`, `node_type` (default `"fact"`), `tags`

### `memory_graph_query`

Query graph by tag or type.

**Parameters:** `layer`, `user_id`, `tag`, `node_type`, `limit`

### `memory_stats`

Memory statistics across all layers.

**Parameters:** `layer`, `user_id`

**Response:**
```json
{
  "l1_buffer": 5, "l2_sessions": 12, "l3_episodes": 8,
  "l4_facts": 45, "wiki_pages": 20, "graph_nodes": 30
}
```

### `memory_context_inject`

Compressed summary for prompt injection (L4 top-10 + L3 top-3 + L1 recent-5 + wiki-3).

**Parameters:** `layer`, `user_id`

```python
result = await mcp.call_tool("memory_context_inject", {
    "layer": "user", "user_id": "alice"
})
# {"context": "FACTS: name=Alice\nEPISODES: Met team...\nRECENT: user: Hello\nWIKI: [diary] Day 1",
#  "l4_facts_count": 10, "l3_episodes_count": 3, ...}
```

---

## Operations Tools (8 tools)

### `memory_api_key`

Manage API keys.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `action` | string | `"list"` | `"create"`, `"revoke"`, or `"list"` |
| `user_id` | string | `"default"` | User to create key for |
| `label` | string | `""` | Optional label |
| `api_key` | string | `""` | Key to revoke |

```python
# Create
result = await mcp.call_tool("memory_api_key", {
    "action": "create", "user_id": "alice", "label": "prod"
})
# {"api_key": "ak_...", "user_id": "alice", "label": "prod"}

# List
result = await mcp.call_tool("memory_api_key", {"action": "list"})
```

### `memory_backup`

Manage backups.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `action` | string | `"status"` | `"now"`, `"list"`, `"restore"`, or `"status"` |
| `backup_name` | string | `""` | Backup to restore |

```python
# Create backup
result = await mcp.call_tool("memory_backup", {"action": "now"})

# List backups
result = await mcp.call_tool("memory_backup", {"action": "list"})
```

### `memory_saga`

Run sagas with auto-rollback on failure.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `action` | string | `"consolidate"` | `"consolidate"` or `"backup"` |
| `user_id` | string | `"default"` | User identifier (consolidate only) |

```python
# Consolidation: gather → distill → promote
result = await mcp.call_tool("memory_saga", {
    "action": "consolidate", "user_id": "alice"
})

# Backup: copy → verify
result = await mcp.call_tool("memory_saga", {"action": "backup"})
```

### `memory_data`

Import/export memory data.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `action` | string | `"list"` | `"export"`, `"import"`, or `"list"` |
| `user_id` | string | `"default"` | User to export |
| `file_path` | string | `""` | File to import |
| `target_user_id` | string | `""` | Import as this user |

```python
# Export
result = await mcp.call_tool("memory_data", {
    "action": "export", "user_id": "alice"
})

# Import
result = await mcp.call_tool("memory_data", {
    "action": "import", "file_path": "/path/to/export.json", "target_user_id": "bob"
})
```

### `memory_sync_replica`

Sync read-only replica for dashboard/metrics.

**Response:** `{"synced": {...}, "ready": true}`

### `memory_cleanup`

Full cleanup: deduplicate, archive, clean staging.

**Parameters:** `user_id`, `retention_days` (default 30)

### `memory_lucidity_purge`

Emergency purge of all user data from last N hours.

**Parameters:** `user_id`, `hours` (default 24)

**Cleans:** core_memory, episodes, staging, audit_log, graph_nodes.

```python
result = await mcp.call_tool("memory_lucidity_purge", {
    "user_id": "alice", "hours": 24
})
# {"core_memory": 15, "episodes": 8, "staging": 12, "audit": 50, "graph_nodes": 5}
```

### `memory_search_rrf`

Hybrid search using Reciprocal Rank Fusion (FTS5 + vector similarity) with pluggable strategies.

**Parameters:** `query`, `user_id`, `limit`, `strategy`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | `""` | Search query |
| `user_id` | string | `"default"` | User identifier |
| `limit` | int | `10` | Max results |
| `strategy` | string | `"hybrid"` | Search strategy: `"fts"`, `"mib"`, `"hybrid"`, or `"auto"` |

**Strategies:**
- `fts`: Full-text search via FTS5 (fast, keyword-based)
- `mib`: Binary embedding similarity (semantic)
- `hybrid`: Combined FTS5 + MIB with Scorer ranking (best recall)
- `auto`: Automatically selects FTS for short queries, hybrid for longer ones

```python
# FTS-only (fast keyword search)
result = await mcp.call_tool("memory_search_rrf", {
    "query": "redis config", "user_id": "alice", "limit": 5, "strategy": "fts"
})

# MIB-only (semantic similarity)
result = await mcp.call_tool("memory_search_rrf", {
    "query": "memory management patterns", "user_id": "alice", "limit": 5, "strategy": "mib"
})

# Hybrid (best recall)
result = await mcp.call_tool("memory_search_rrf", {
    "query": "python best practices", "user_id": "alice", "limit": 5, "strategy": "hybrid"
})

# Auto (recommended)
result = await mcp.call_tool("memory_search_rrf", {
    "query": "how to set up caching", "user_id": "alice", "limit": 5, "strategy": "auto"
})
```
