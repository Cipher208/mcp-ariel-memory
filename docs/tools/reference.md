# MCP Tools Reference

All 19 tools accept a `layer` parameter (`user` or `agent`) to target the appropriate memory layer.

## Memory Operations

### memory_remember

Store a new memory entry.

```json
{
  "layer": "user",
  "content": "I prefer dark mode",
  "kind": "preference",
  "importance": 3,
  "entities": ["display", "theme"],
  "tags": ["ui", "preference"]
}
```

### memory_recall

Search memories by query.

```json
{
  "layer": "user",
  "query": "display preferences",
  "limit": 10,
  "strategy": "auto"
}
```

Strategies: `fts` (keyword), `mib` (semantic), `hybrid` (combined), `auto` (adaptive)

### memory_forget

Soft-delete a memory by ID.

```json
{
  "layer": "user",
  "memory_id": "abc123"
}
```

### memory_stats

Get memory statistics.

```json
{
  "layer": "user"
}
```

## Session Operations

### memory_session_create

Create a new session.

```json
{
  "layer": "user",
  "summary": "Discussed architecture decisions"
}
```

### memory_session_list

List recent sessions.

```json
{
  "layer": "user",
  "limit": 10
}
```

## Graph Operations

### memory_graph_add

Add a node to the knowledge graph.

```json
{
  "layer": "user",
  "node_type": "fact",
  "content": "PostgreSQL is used for production"
}
```

### memory_graph_query

Query the knowledge graph.

```json
{
  "layer": "user",
  "query": "database decisions",
  "limit": 10
}
```

### memory_graph_path

Find path between two nodes.

```json
{
  "layer": "user",
  "from_id": "node1",
  "to_id": "node2"
}
```

## Wiki Operations

### memory_wiki_add

Add or update a wiki page.

```json
{
  "layer": "user",
  "title": "Architecture Overview",
  "content": "# Architecture\n\nTwo-layer memory system...",
  "wiki_type": "spec"
}
```

### memory_wiki_search

Search wiki pages.

```json
{
  "layer": "user",
  "query": "architecture",
  "limit": 5
}
```

## Operations

### memory_backup_create

Create a backup.

```json
{
  "layer": "user"
}
```

### memory_backup_list

List available backups.

```json
{
  "layer": "user"
}
```

### memory_export

Export memories to JSON.

```json
{
  "layer": "user",
  "format": "json"
}
```

### memory_import

Import memories from JSON.

```json
{
  "layer": "user",
  "data": "{...}"
}
```

### memory_compress

Compress old memories.

```json
{
  "layer": "user"
}
```

### memory_consolidate

Run memory consolidation.

```json
{
  "layer": "user"
}
```

### memory_dream

Process dream buffer (background consolidation).

```json
{
  "layer": "user"
}
```
