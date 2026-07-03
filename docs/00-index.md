# mcp-ariel-memory — Documentation

**Universal Two-Layer Memory MCP Server**

[![CI](https://github.com/Cipher208/mcp-ariel-memory/actions/workflows/ci.yml/badge.svg)](https://github.com/Cipher208/mcp-ariel-memory/actions/workflows/ci.yml)

Two-layer universal memory for AI agents. Real MCP Python SDK, async, **19 tools** (unified layer-based API), stdio + Streamable HTTP, dashboard, auth + rate limiting, metrics, auto-backups with jitter, wiki with external folders, read-only replica. **Single `memory.db` file** (~22 tables), platform-aware async (aiosqlite on Linux/macOS, sync sqlite3 on Windows), hooks integrated into tool pipeline. **Typed memory** (13 categories with per-type decay/boost). **Importance v2** with 8-signal scorer and background scheduler. **Saga** with retry, idempotent replay, and compensation. **BM25 + char-trigram** conflict similarity.

---

## Installation

### npm (recommended)

```bash
npx mcp-ariel-memory --transport stdio
```

### pip

```bash
pip install git+https://github.com/Cipher208/mcp-ariel-memory.git
python -m mcp_server --transport stdio
```

### Docker

```bash
docker build -t ariel-memory .
docker run -p 8000:8000 ariel-memory
```

### From source

```bash
git clone https://github.com/Cipher208/mcp-ariel-memory.git
cd mcp-ariel-memory
pip install -e ".[all]"
python -m mcp_server --transport stdio
```

---

## Table of Contents

| # | Document | Description |
|---|----------|-------------|
| 01 | [Architecture](01-architecture.md) | Stack, two-layer model, L1-L4, consolidation, 22 DB tables |
| 02 | [MCP Tools](02-mcp-tools.md) | All 19 tools with parameters and examples |
| 03 | [Core Memory](03-core.md) | ReflexBuffer, SessionStore, EpisodicMemory, CoreMemory + typed memory |
| 04 | [Search (RAG)](04-rag.md) | Unified search, BM25 conflict similarity, type-aware boost |
| 05 | [Knowledge Graph](05-graph.md) | EpistemicGraph, TemporalGraph |
| 06 | [Lifecycle](06-lifecycle.md) | Type-aware Forgetting, EmotionTrigger, Consolidation, Importance Scheduler |
| 07 | [Hooks](07-hooks.md) | 24 hooks (12 user + 12 agent), type-aware gating |
| 08 | [Wiki](08-wiki.md) | FileWiki (.md files + FTS5), 14 types |
| 09 | [Features](09-features.md) | Auth, Backup, Dashboard, Audit, RateLimit, Secrets |
| 10 | [Shared](10-shared.md) | Saga+Retry+Idempotency, Importance Scorer, Middleware, Embeddings |
| 11 | [Operations](11-operations.md) | Transports, Health, Auth, Scheduler, Configuration |
| 12 | [Testing](12-testing.md) | pytest (338 tests + 25 Hypothesis), benchmarks, project structure |

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
- **MCP Tools:** 19
- **Tests:** 338 passed (25 property-based Hypothesis)
- **Python files:** 70
- **DB tables:** 23
- **Hooks:** 24
- **Wiki types:** 14
- **Health endpoints:** /health, /ready, /alive
- **Platform:** Windows, Linux, macOS, Docker
- **Python:** 3.10–3.13
- **Encryption:** libsodium secretbox (AES-256-GCM)
- **Graceful shutdown:** SIGTERM/SIGINT handling
