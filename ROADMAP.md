# ROADMAP

> Future development plans for mcp-ariel-memory after v1.0.0.

---

## 1. Publishing & Distribution

- [ ] **PyPI publication** — `twine upload dist/*`, requires `~/.pypirc` with API token
- [ ] **GitHub Release** — create tag `v1.0.0` + release with CHANGELOG
- [ ] **MCP Registry update** — fix description: "37 tools" → "19 tools"
- [ ] **Docker Hub** — publish `ariel-memory` image
- [ ] **npm version** — verify `mcp-ariel-memory@1.0.0` is current, bump if needed

## 2. Architecture & Performance

- [ ] **Float blobs migration** — optionally remove float embeddings (keep_float_blobs=false), keep binary only
- [ ] **FTS5 improvements** — add triggers for auto-sync content (currently manual INSERT)
- [ ] **Connection pooling** — SQLite WAL mode + read/write split (read-only replica)
- [ ] **Migrations** — mechanism for ALTER TABLE without downtime (currently version-based)
- [ ] **Extended indexes** — add indexes for `temporal_events`, `temporal_links`
- [ ] **Expand batched reads** — apply batch processing to all large queries (not just binary search)

## 3. RAG & Search

- [ ] **Supervised thresholds** — auto-train on production data (currently manual)
- [ ] **Hybrid reranker** — add cross-encoder reranking after RRF
- [ ] **Embedding cache** — implement LRU cache for repeated queries
- [ ] **Auto-strategy** — make `auto` strategy smarter (based on query analytics)
- [ ] **Query expansion** — add synonyms for FTS5

## 4. Bug Fixes & Cleanup

- [ ] **Deprecated API cleanup** — remove `search_rrf()` and `search_binary()` in next major version
- [ ] **Tool rename** — `memory_search_rrf` → `memory_search` (after MCP Registry update)
- [ ] **CLI improvements** — add `--version` flag, improve help messages
- [ ] **HTTP transport** — add OAuth2/Bearer token for production deployments
- [ ] **Dashboard** — add live updates (WebSocket), improve UI

## 5. Testing & CI

- [ ] **Coverage** — add `--cov` in CI, reach 90% coverage
- [ ] **Load testing** — add k6/Artillery tests for production simulation
- [ ] **Fuzz testing** — add fuzz tests for parsing and validation
- [ ] **Cross-platform testing** — add Windows to CI matrix (currently Linux only)
- [ ] **Benchmark tracking** — store benchmark results in CI, track regressions

## 6. Documentation

- [ ] **API Reference** — auto-generate from docstrings (Sphinx/MkDocs)
- [ ] **Architecture diagrams** — add mermaid diagrams to docs
- [ ] **Contributing guide** — add CONTRIBUTING.md with contributor instructions
- [ ] **Examples** — add usage examples for Claude Desktop, Hermes, etc.
- [ ] **Migration guide** — add migration guide from previous versions

## 7. Security

- [ ] **RBAC** — add role-based model for multi-tenant deployments
- [ ] **Audit logging** — improve log format (JSON structured logging)
- [ ] **Rate limiting** — add adaptive rate limiting based on load
- [ ] **Encryption at rest** — add AES-256-GCM for database files
- [ ] **Input validation** — add validation at MCP tools level (Pydantic schemas)

## 8. Integrations

- [ ] **LangChain** — add LangChain integration (memory retriever)
- [ ] **AutoGen** — add AutoGen framework support
- [ ] **CrewAI** — add CrewAI support
- [ ] **LlamaIndex** — add LlamaIndex integration
- [ ] **OpenAI plugin** — add OpenAI plugin for GPT-4

## 9. Hooks & Extensibility

- [ ] **Plugin system** — implement plugins for custom hooks
- [ ] **Webhook support** — add webhook callbacks for external services
- [ ] **GraphQL API** — add GraphQL endpoint
- [ ] **gRPC support** — add gRPC transport (for high performance)
- [ ] **WebSocket** — add WebSocket for real-time updates

## 10. Operations & Observability

### 10.1 Monitoring & Alerting

- [ ] **Prometheus metrics** — add Prometheus-compatible metrics endpoint (`/metrics`)
- [ ] **Alerting** — add alerting for critical failures
- [ ] **Telegram webhook** — send alerts to Telegram channel via bot API
- [ ] **Discord webhook** — send alerts to Discord channel via webhook URL
- [ ] **Webhook alerting** — configurable webhook targets (Telegram, Discord, Slack, custom)

### 10.2 Health & Readiness

- [ ] **Healthcheck endpoint** — `GET /health` — returns `{"status": "ok"}` with uptime, version, DB status
- [ ] **Readiness probe** — `GET /ready` — returns `{"ready": true}` when DB connected, migrations done, hooks loaded
- [ ] **Liveness probe** — `GET /alive` — simple heartbeat for container orchestrators (Kubernetes, Docker)
- [ ] **OpenTelemetry** — add OpenTelemetry tracing for distributed observability

### 10.3 Graceful Shutdown & Signal Handling

- [ ] **Signal handling** — handle `SIGTERM` and `SIGINT` for graceful shutdown
- [ ] **Drain connections** — wait for in-flight requests to complete before exit
- [ ] **Close DB connections** — properly close all SQLite connections on shutdown
- [ ] **Stop background tasks** — cancel saga watchdog, backup cron, and middleware loops
- [ ] **State persistence** — save saga state before shutdown for recovery on restart

## 11. New Features

- [ ] **Multi-language support** — add support for multiple languages (CJK, Arabic)
- [ ] **Voice input** — add voice input support (via Whisper API)
- [ ] **Image support** — add image embedding (CLIP, DALL-E)
- [ ] **Video support** — add video embedding (CLIP, VideoMAE)
- [ ] **Code search** — add semantic code search (embed tree-sitter)

## 12. Tutorials & Launch Demo

- [ ] **Launch demo script** — single script (`demo.py`) that:
  - Starts the server
  - Creates test data (users, memories, wiki entries, graph nodes)
  - Runs all search strategies (FTS, MIB, hybrid)
  - Demonstrates hooks, saga, and backup
  - Outputs formatted results with timing
- [ ] **Getting started guide** — step-by-step tutorial for new users
- [ ] **Quick start with Docker** — one-command Docker setup with sample data
- [ ] **Hermes integration guide** — how to deploy on Hermes agent
- [ ] **MCP client examples** — Python and JavaScript client examples

## 13. Operational Tasks

- [ ] **Remove deprecated features** — remove deprecated wrappers (search_rrf, search_binary)
- [ ] **Cleanup** — remove unused tables, indexes, functions
- [ ] **Optimization** — optimize memory usage, CPU, I/O
- [ ] **Scalability** — test with 1M+ records
- [ ] **Documentation** — update all docs for v2.0

---

**Note:** This file is updated as progress is made. Priorities are determined by user feedback and production usage.
