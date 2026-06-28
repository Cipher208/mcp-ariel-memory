# mcp-ariel-memory

**Universal Two-Layer Memory MCP Server**

[![CI](https://github.com/ariel-memory/mcp-ariel-memory/actions/workflows/ci.yml/badge.svg)](https://github.com/ariel-memory/mcp-ariel-memory/actions/workflows/ci.yml)

Two-layer universal memory for AI agents. Real MCP Python SDK, async, **37 tools**, stdio + Streamable HTTP, dashboard with auth + rate limiting, metrics, auto-backups with jitter, wiki with external folders, read-only replica, OpenAPI spec.

[English](README_EN.md) | Русский

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
docker run -p 8000:8000 ariel-memory
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

---

## Documentation

| # | Document | Description |
|---|----------|-------------|
| 01 | [Architecture](docs/01-architecture.md) | Stack, two-layer model, L1-L4, consolidation |
| 02 | [MCP Tools](docs/02-mcp-tools.md) | All 37 tools with parameters and examples |
| 03 | [Core Memory](docs/03-core.md) | ReflexBuffer, SessionStore, EpisodicMemory, CoreMemory |
| 04 | [Search (RAG)](docs/04-rag.md) | FTS5, RRF, RetrievalRouter, ConflictResolver |
| 05 | [Knowledge Graph](docs/05-graph.md) | EpistemicGraph, TemporalGraph |
| 06 | [Lifecycle](docs/06-lifecycle.md) | Forgetting, EmotionTrigger, Consolidation |
| 07 | [Hooks](docs/07-hooks.md) | 24 hooks (12 user + 12 agent) |
| 08 | [Wiki](docs/08-wiki.md) | FileWiki (files as source of truth + FTS5) |
| 09 | [Features](docs/09-features.md) | Auth, Backup, Dashboard, Audit, RateLimit |
| 10 | [Shared](docs/10-shared.md) | Cache, Saga+Watchdog, Middleware, Embeddings, Metrics |
| 11 | [Operations](docs/11-operations.md) | Transports, Dashboard, Auth, Backup, Configuration |
| 12 | [Testing](docs/12-testing.md) | pytest, project structure |

---

## Status

- **MCP Tools:** 37
- **pytest:** 56/56
- **Python files:** 70
- **DB tables:** 21
- **Hooks:** 24
- **Wiki types:** 14
- **DB migrations:** 3
