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

- [x] **Float blobs migration** — `keep_float_blobs` config + migration v7 (drop column)
- [x] **Expand batched reads** — fetchmany(1000) in forgetting, scheduler
- [x] **Connection pooling** — cache_size=64MB, temp_store=MEMORY
- [ ] **HNSW index** — integrate hnswlib for binary search (replaces O(n) scan). Config: `binary.index: "hnsw"` with fallback to brute-force. Requires migration for index storage.
- [ ] **FTS5 improvements** — add triggers for auto-sync content (currently manual INSERT)
- [ ] **Extended indexes** — add indexes for `temporal_events`, `temporal_links`

## 3. RAG & Search

- [x] **Supervised thresholds** — per-dimension MIB thresholds from labeled pairs (implemented)
- [ ] **Hybrid reranker** — add cross-encoder reranking after RRF
- [ ] **Embedding cache** — implement LRU cache for repeated queries
- [ ] **Auto-strategy** — make `auto` strategy smarter (based on query analytics)
- [ ] **Query expansion** — add synonyms for FTS5

## 4. Bug Fixes & Cleanup

- [x] **Deprecated API cleanup** — removed `search_rrf()`, `search_binary()` (A7)
- [ ] **Tool rename** — `memory_search_rrf` → `memory_search` (after MCP Registry update)
- [ ] **CLI improvements** — add `--version` flag, improve help messages
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

## 7. Security

- [ ] **RBAC** — add role-based model for multi-tenant deployments
- [ ] **Audit logging** — improve log format (JSON structured logging)
- [ ] **Rate limiting** — add adaptive rate limiting based on load
- [ ] **Input validation** — add validation at MCP tools level (Pydantic schemas)

## 8. Integrations

- [ ] **LangChain** — add LangChain integration (memory retriever)
- [ ] **AutoGen** — add AutoGen framework support
- [ ] **CrewAI** — add CrewAI support
- [ ] **LlamaIndex** — add LlamaIndex integration

## 9. Hooks & Extensibility

- [ ] **Plugin system** — implement plugins for custom hooks
- [ ] **Webhook support** — add webhook callbacks for external services
- [ ] **GraphQL API** — add GraphQL endpoint

## 10. Operations & Observability

### 10.1 Monitoring & Alerting

- [ ] **Prometheus metrics** — add Prometheus-compatible metrics endpoint (`/metrics`)
- [ ] **Telegram webhook** — send alerts to Telegram channel via bot API
- [ ] **Discord webhook** — send alerts to Discord channel via webhook URL

### 10.2 Health & Readiness

- [x] **Healthcheck endpoint** — `GET /health` with status, version, uptime, DB connectivity
- [x] **Readiness probe** — `GET /ready` with DB + migrations status
- [x] **Liveness probe** — `GET /alive` heartbeat
- [ ] **OpenTelemetry** — add OpenTelemetry tracing for distributed observability

### 10.3 Graceful Shutdown & Signal Handling

- [x] **Signal handling** — handle `SIGTERM` and `SIGINT` for graceful shutdown
- [x] **Stop background tasks** — cancel saga watchdog, backup cron, read_only_replica
- [ ] **Drain connections** — wait for in-flight requests to complete before exit

## 11. Typed Memory & Importance

- [x] **Typed Memory** — 13 categories with per-type retention, decay, and boost
- [x] **Memory kinds** — instruction, fact, decision, goal, preference, commitment, relationship, observation, rule, todo, question, hypothesis, context
- [x] **Type-aware forgetting** — instruction/rule/commitment never decay/archive
- [x] **Type-aware consolidation** — low importance instruction/rule/commitment still promote
- [x] **Type-aware hooks** — importance gate uses type policy
- [x] **Type-aware RAG boost** — search results boosted by query-type matching
- [x] **Typed export CLI** — export, reclassify, backfill bulk operations
- [x] **Importance v2** — 8-signal scorer (base, length, question, tech, emotional, novelty, retrieval, noise)
- [x] **Importance scheduler** — background daemon for periodic re-scoring
- [x] **Importance middleware** — uses ImportanceScorer instead of naive heuristic

## 12. Saga & Reliability

- [x] **Saga retry** — exponential backoff with configurable retry_attempts/retry_on
- [x] **Saga idempotency** — idempotency_key_fn + saga_step_log prevents duplicate effects
- [x] **Saga encryption** — atomic encrypted state writes with legacy rotation
- [x] **Saga compensation** — saves state before compensation, archives deleted entries
- [x] **Saga cleanup** — handles stuck/failed/manual_review_required states

## 13. RAG Improvements

- [x] **Unified search** — `search(query, strategy=...)` with fts/mib/hybrid/auto
- [x] **BM25 conflict similarity** — char-trigram Jaccard fallback
- [x] **Type-aware search boost** — boost_for_query based on memory_kind
- [x] **Batched embedding reads** — fetchmany(1000) instead of fetchall
- [x] **epi_tags table** — indexed JOIN for fast tag lookups (1850 ops/s)
- [x] **rag_chunks index** — (page_id, chunk_index) for JOINs (3537 ops/s)
- [x] **Performance benchmarks** — FTS 1817, MIB 215, hybrid 178 ops/s

## 14. Tutorials & Launch Demo

- [x] **Launch demo script** — `demo.py` creates test data and shows features
- [ ] **Getting started guide** — step-by-step tutorial for new users
- [ ] **Quick start with Docker** — one-command Docker setup with sample data
- [ ] **Hermes integration guide** — how to deploy on Hermes agent

## 15. Operational Tasks

- [x] **Remove deprecated features** — search_rrf, search_binary removed
- [ ] **Cleanup** — remove unused tables, indexes, functions
- [ ] **Optimization** — optimize memory usage, CPU, I/O
- [ ] **Scalability** — test with 1M+ records

## 16. Hermes Memory Integration

- [ ] **Archive config** — expose `archive_threshold_days`, `archive_min_importance`, `forgetting.decay_rate` via MCP tools for agent self-configuration
- [ ] **Memory health check** — add `memory_stats` tool to check archive size, forgetting schedule, typed memory distribution
- [ ] **Auto-archival** — implement cron-based archival in Hermes (currently only `archive_threshold_days` is configurable from config)

---

**Completed:** 21/58 items
**Last updated:** 2026-06-30
