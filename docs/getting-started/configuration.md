# Configuration

## Config File

Location: `config.yaml` (project root or `~/.mcp-ariel-memory/config.yaml`)

```yaml
# Memory settings
memory:
  max_l1_size: 50          # ReflexBuffer ring buffer size
  max_l2_sessions: 100     # EpisodicMemory max sessions
  max_l3_entries: 500      # SessionStore max entries
  max_l4_facts: 5000       # CoreMemory max facts

# RAG settings
rag:
  chunk_size: 512
  chunk_overlap: 50
  search_strategy: auto    # fts | mib | hybrid | auto

# Crypto
crypto:
  master_key_hex: ""       # Override keychain (dev only)

# Hooks
hooks:
  user_importance_gate: 0.3
  agent_importance_gate: 0.3
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_MASTER_KEY` | auto-generated | Master key for envelope encryption |
| `MCP_MEMORY_DATA_DIR` | `~/.mcp-ariel-memory` | Data directory for SQLite databases |
| `MCP_AUTH_TOKEN` | auto-generated | Bearer token for HTTP transport |
| `MCP_SERVER_PORT` | 8000 | HTTP server port |
| `BACKUP_CRON_DISABLED` | false | Disable backup cron daemon |

## Key Resolution Order

Master key is resolved in this order:

1. **OS keychain** (keyring library) — recommended for production
2. **config.yaml** (`crypto.master_key_hex`)
3. **.env file** (`MCP_MASTER_KEY=...`) — local development only
4. **Environment variable** (`MCP_MASTER_KEY`)
5. **Auto-generate** — creates key and saves to `.env`

## Transports

### stdio (default)

```bash
python -m mcp_server --transport stdio
```

### HTTP (Streamable)

```bash
python -m mcp_server --transport http --port 8000
```

### With auth

```bash
python -m mcp_server --transport http --auth
```
