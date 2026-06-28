# MCP Tools — Full Reference (37 tools)

## User Layer (10 tools)

### `memory_user_remember`

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

### `memory_user_recall`

Search user memory (L3 + L4).

**Parameters:** `user_id`, `query`, `limit` (default 10)

**Response:** `{"results": [{"key": "name", "value": "Alice", "importance": 0.9}], "count": 1}`

```python
result = await mcp.call_tool("memory_user_recall", {
    "user_id": "alice", "query": "name"
})
```

### `memory_user_forget`

Delete a fact from L4.

**Parameters:** `user_id`, `key`

**Response:** `{"deleted": true}` or `{"deleted": false}`

```python
await mcp.call_tool("memory_user_forget", {"user_id": "alice", "key": "hobby"})
```

### `memory_user_session_start`

Start a new session.

**Response:** `{"session_id": "sess_alice_1782036546_0b6ec91f"}`

### `memory_user_session_end`

End a session with summary.

**Parameters:** `user_id`, `session_id`, `summary`

### `memory_user_episode_save`

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

### `memory_user_episode_recall`

Find episodes (all or by tag).

**Parameters:** `user_id`, `tag` (optional), `limit`

```python
result = await mcp.call_tool("memory_user_episode_recall", {"user_id": "alice", "tag": "work"})
```

### `memory_user_graph_add`

Add node to epistemic graph.

**Parameters:** `content`, `node_type` (default `"fact"`), `tags`

### `memory_user_graph_query`

Query graph by tag or type.

**Parameters:** `user_id`, `tag`, `node_type`, `limit`

### `memory_user_stats`

Memory statistics across all layers.

**Response:**
```json
{
  "l1_buffer": 5,
  "l2_sessions": 12,
  "l3_episodes": 8,
  "l4_facts": 45,
  "wiki_pages": 20,
  "graph_nodes": 30
}
```

---

## Agent Layer (10 tools)

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

## Auth (3 tools)

| Tool | Parameters | Response |
|------|-----------|----------|
| `memory_create_api_key` | `user_id`, `label` | `{"api_key": "ak_..."}` |
| `memory_revoke_api_key` | `api_key` | `{"revoked": true}` |
| `memory_list_api_keys` | — | `{"keys": [...]}` |

---

## Backup (4 tools)

| Tool | Parameters | Response |
|------|-----------|----------|
| `memory_backup_now` | — | `{"path": "..."}` |
| `memory_backup_list` | — | `{"backups": [...]}` |
| `memory_backup_restore` | `backup_name` | `{"restored": [...]}` |
| `memory_backup_status` | — | `{"running": true, "jitter_seconds": 3600, ...}` |

---

## Saga (2 tools)

### `memory_saga_consolidate`

Consolidation saga: gather → distill → promote. Auto-rollback + watchdog.

### `memory_saga_backup`

Backup saga: copy → verify. Auto-rollback + persistence.

---

## Replica (1 tool)

### `memory_sync_replica`

Sync read-only replica.

**Parameters:** `replica_path`

---

## Import/Export (3 tools)

| Tool | Parameters | Response |
|------|-----------|----------|
| `memory_export` | `user_id`, `format` | Exports memory to JSON/JSONL |
| `memory_import` | `user_id`, `data`, `format` | Imports memory from JSON/JSONL |
| `memory_list_exports` | — | Lists available exports |

---

## Maintenance (1 tool)

### `memory_cleanup`

Full cleanup: deduplication, archival, staging, audit, backup, sagas.

**Parameters:** `user_id`, `older_than_days` (default 30)

---

## Emergency (1 tool)

### `memory_lucidity_purge`

Emergency purge of all user data from last N hours (data leak scenario).

**Parameters:** `user_id`, `hours` (default 24)

**Cleans:** core_memory, episodes, staging, audit_log, graph_nodes from last N hours.

```python
result = await mcp.call_tool("memory_lucidity_purge", {
    "user_id": "alice", "hours": 24
})
# {"core_memory": 15, "episodes": 8, "staging": 12, "audit": 50, "graph_nodes": 5}
```

---

## Context Injection (1 tool)

### `memory_user_context_inject`

Compressed summary for prompt injection (L4 top-10 + L3 top-3 + L1 recent-5 + wiki-3).

**Parameters:** `user_id`

```python
result = await mcp.call_tool("memory_user_context_inject", {"user_id": "alice"})
# {"context": "FACTS: name=Alice\nEPISODES: Met team...\nRECENT: user: Hello\nWIKI: [diary] Day 1",
#  "l4_facts_count": 10, "l3_episodes_count": 3, ...}
```

---

## Hybrid Search (1 tool)

### `memory_search_rrf`

Hybrid search using Reciprocal Rank Fusion (FTS5 + vector similarity). Falls back to LIKE if FTS5 unavailable.

**Parameters:** `query`, `user_id`, `limit`

```python
result = await mcp.call_tool("memory_search_rrf", {
    "query": "python best practices", "user_id": "alice", "limit": 5
})
```
