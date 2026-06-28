# mcp-ariel-memory — Documentation

**Universal Two-Layer Memory MCP Server**

[![CI](https://github.com/ariel-memory/mcp-ariel-memory/actions/workflows/ci.yml/badge.svg)](https://github.com/ariel-memory/mcp-ariel-memory/actions/workflows/ci.yml)

Two-layer universal memory for AI agents. Real MCP Python SDK, async, **37 tools**, stdio + Streamable HTTP, dashboard, auth + rate limiting, metrics, auto-backups with jitter, wiki with external folders, read-only replica, OpenAPI. **Single `memory.db` file** (~21 tables), native async via asyncio+sqlite3, hooks integrated into tool pipeline.

---

## Table of Contents

| # | Document | Description |
|---|----------|-------------|
| 01 | [Architecture](01-architecture.md) | Stack, two-layer model, L1-L4, consolidation |
| 02 | [MCP Tools](02-mcp-tools.md) | All 37 tools with parameters and examples |
| 03 | [Core Memory](03-core.md) | ReflexBuffer, SessionStore, EpisodicMemory, CoreMemory |
| 04 | [Search (RAG)](04-rag.md) | FTS5 + fallback, RRF, RetrievalRouter, ConflictResolver |
| 05 | [Knowledge Graph](05-graph.md) | EpistemicGraph, TemporalGraph |
| 06 | [Lifecycle](06-lifecycle.md) | Forgetting, EmotionTrigger, Consolidation |
| 07 | [Hooks](07-hooks.md) | 24 hooks (12 user + 12 agent) |
| 08 | [Wiki](08-wiki.md) | FileWiki (.md files + FTS5) |
| 09 | [Features](09-features.md) | Auth, Backup, Dashboard, Audit, RateLimit |
| 10 | [Shared](10-shared.md) | Cache, Saga+Watchdog, Middleware, Embeddings, Metrics, DreamBuffer, Archive, Migrations, Read-only replica |
| 11 | [Operations](11-operations.md) | Transports, Dashboard, Auth, Backup, Configuration |
| 12 | [Testing](12-testing.md) | pytest, project structure |

---

## Quick Start

```bash
git clone <repo> && cd mcp-ariel-memory
pip install -e ".[all]"
python -m mcp_ariel_memory --transport stdio
```

### Docker

```bash
docker build -t ariel-memory .
docker run -v $(pwd)/config.yaml:/app/config.yaml:ro -p 8000:8000 ariel-memory
# Or docker-compose (auto-mounts config.yaml)
docker-compose up
```

### Claude Desktop

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
