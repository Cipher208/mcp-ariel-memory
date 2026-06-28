# mcp-ariel-memory — Documentation

**Universal Two-Layer Memory MCP Server**

[![CI](https://github.com/faustovo2003-commits/mcp-ariel-memory/actions/workflows/ci.yml/badge.svg)](https://github.com/faustovo2003-commits/mcp-ariel-memory/actions/workflows/ci.yml)

Two-layer universal memory for AI agents. Real MCP Python SDK, async, **37 tools**, stdio + Streamable HTTP, dashboard, auth + rate limiting, metrics, auto-backups with jitter, wiki with external folders, read-only replica. **Single `memory.db` file** (~21 tables), platform-aware async (aiosqlite on Linux/macOS, sync sqlite3 on Windows), hooks integrated into tool pipeline.

---

## Installation

### npm (recommended)

```bash
npx mcp-ariel-memory --transport stdio
```

### pip

```bash
pip install git+https://github.com/faustovo2003-commits/mcp-ariel-memory.git
python -m mcp_server --transport stdio
```

### Docker

```bash
docker build -t ariel-memory .
docker run -p 8000:8000 ariel-memory
```

### From source

```bash
git clone https://github.com/faustovo2003-commits/mcp-ariel-memory.git
cd mcp-ariel-memory
pip install -e ".[all]"
python -m mcp_server --transport stdio
```

---

## Table of Contents

| # | Document | Description |
|---|----------|-------------|
| 01 | [Architecture](01-architecture.md) | Stack, two-layer model, L1-L4, consolidation, 21 DB tables |
| 02 | [MCP Tools](02-mcp-tools.md) | All 37 tools with parameters and examples |
| 03 | [Core Memory](03-core.md) | ReflexBuffer, SessionStore, EpisodicMemory, CoreMemory |
| 04 | [Search (RAG)](04-rag.md) | FTS5 + fallback, RRF, RetrievalRouter, ConflictResolver |
| 05 | [Knowledge Graph](05-graph.md) | EpistemicGraph, TemporalGraph |
| 06 | [Lifecycle](06-lifecycle.md) | Forgetting, EmotionTrigger, Consolidation |
| 07 | [Hooks](07-hooks.md) | 24 hooks (12 user + 12 agent) |
| 08 | [Wiki](08-wiki.md) | FileWiki (.md files + FTS5), 14 types |
| 09 | [Features](09-features.md) | Auth, Backup, Dashboard, Audit, RateLimit |
| 10 | [Shared](10-shared.md) | Cache, Saga+Watchdog, Middleware, Embeddings, Metrics |
| 11 | [Operations](11-operations.md) | Transports, Dashboard, Auth, Backup, Configuration |
| 12 | [Testing](12-testing.md) | pytest (104 tests), project structure |

---

## Quick Start

### Claude Desktop

```json
{
  "mcpServers": {
    "ariel-memory": {
      "command": "npx",
      "args": ["mcp-ariel-memory", "--transport", "stdio"]
    }
  }
}
```

### HTTP Server

```bash
python -m mcp_server --transport http --port 8000
```

---

## Status

- **Version:** 1.0.0
- **MCP Tools:** 37
- **Tests:** 104 passed
- **Python files:** 70
- **DB tables:** 21
- **Hooks:** 24
- **Wiki types:** 14
- **Platform:** Windows, Linux, macOS, Docker
