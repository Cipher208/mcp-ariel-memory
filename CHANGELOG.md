# Changelog

All notable changes to mcp-ariel-memory are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

## [1.0.0] - 2026-06-29

### Fixed
- **P0** `AgentHooks._importance_gate` missing — `memory_remember(layer="agent")` crashed with `AttributeError`. Added method with agent-specific keyword scoring.
- **P1** Backup cron `db_files` duplicated same filename 10x. Copy-paste error — now single entry.
- **P1** `backup_now()`, `list_backups()`, `restore()` sync methods called with `await` in `tools_ops.py`. Removed `await`.
- **P1** `AuditTrail._get_conn()` / `EpistemicGraph._get_conn()` don't exist. Fixed to use `conn_manager.get("memory.db")`.
- **P1** HTTP transport error handling — `mcp.run(transport="streamable-http")` failed silently. Added try/except with logging.
- **P1** Auth middleware returned 401 for MCP clients on `/mcp` endpoint. Skip auth for `/mcp` and `/health`.
- **P1** MCP protocol violation — `tools/list` called before `initialized` notification. Added protocol docs.
- **P2** `is_hook_enabled()` returned `False` for all hooks. Known hooks now default to `True`.
- **P2** `_calculate_importance` too simple (length/signs only). Added semantic keywords (important, critical, urgent, etc.).
- **P2** `_run_async` thread safety — added `asyncio.Lock` for concurrent SQLite access.
- **P3** `config.py` crashed with `FileNotFoundError` on fresh install. Added try/except fallback.
- Auto-generate master key on first run — no more `RuntimeError: No master key found`.
- `None` scores in `_materialize_candidates` merge — LIKE-fallback results now handled.
- Deprecation warnings on deprecated test calls (`search_rrf`/`search_binary`) — migrated to `search(strategy=...)`.
- `Saga.get_state()` returned reference to `_data` — now returns copy.
- `Saga._compensate()` didn't save state before compensation — added `_save_state()` before loop.
- `SagaWatchdog.cleanup_completed()` only cleaned completed/compensated — added stuck/failed/manual_review_required.
- `Saga._data` wasn't saved before `update()` — moved `step.data` assignment before `_data.update()` to preserve pre-step state.
- `rag/engine.py` empty embedding guard — added `len(emb) > 0` check before `struct.pack`.
- Missing indexes on `updated_at`/`timestamp` columns — added for `core_memory`, `user_wiki`, `agent_wiki`, `wiki_index`, `audit_log`.
- `query_by_tag()` used `LIKE` on JSON — extracted tags to `epi_tags` table with indexed JOIN (1850 ops/s).
- `_search_binary()` loaded all rows into memory — changed to batched `fetchmany(1000)`.
- Missing `rag_chunks(page_id, chunk_index)` index — added for JOIN performance (3537 ops/s).
- `GET /health` — health check endpoint with status, version, uptime, DB connectivity.
- `GET /ready` — readiness probe for Kubernetes (DB + migrations OK).
- `GET /alive` — liveness heartbeat for container orchestrators.
- Graceful shutdown — SIGTERM/SIGINT handler stops backup_cron, saga_watchdog, read_only_replica.
- `demo.py` — launch demo script creating test data and showing all features.

### Added
- `AgentHooks._importance_gate` with agent-specific keywords (error, decision, principle, lesson, pattern).
- `--no-auth` flag for development servers.
- `--dashboard` flag (dashboard disabled by default for startup performance).
- Auto-generated MCP master key with `.env` persistence on first run.
- `try/except` wrapping all hook calls — single hook crash no longer breaks tool execution.
- Integration test for `memory_remember(layer="agent")` via FakeApp.
- Unit test for `AgentHooks._importance_gate`.
- Config fallback for missing `config.yaml` files.
- Hermes YAML config examples in README.
- `CHANGELOG.md` with full release history.
- `rag.storage.keep_float_blobs` config option — make float embeddings optional (default: true).
- 6 new tests for `features/secrets.py` — `_load_master_key`, `_save_dotenv`, `_load_dotenv`, `_get_master_key` caching.
- MultiSourceRAG documentation in `docs/04-rag.md`.
- 5 database indexes on `updated_at`/`timestamp` columns.
- `epi_tags` table with indexed JOIN for fast tag lookups (migration v3).
- `rag_chunks(page_id, chunk_index)` index for JOINs (migration v4).
- Batched embedding reads in `search_binary()` (fetchmany with BATCH_SIZE=1000).
- Performance benchmarks: FTS 1817 ops/s, MIB 215 ops/s, hybrid 178 ops/s, epi_tags JOIN 1850 ops/s, rag_chunks JOIN 3537 ops/s.

### Changed
- Dashboard `features.dashboard: false` by default (was `true`).
- Test suite: deprecated `search_rrf()` / `search_binary()` calls migrated to unified `search(strategy=...)`.
- `docs/07-hooks.md`: added `AgentHooks._importance_gate` documentation.
- `docs/11-operations.md`: added `--no-auth`, auto-generated keys, dashboard flag docs.
- Test count: 246 passing (was 239).

### Docs
- MCP initialization protocol in `docs/11-operations.md`.
- Security/encryption documentation for API keys and bearer tokens.
- Hermes YAML config in both README and README_EN.
- Updated README features table with MultiSourceRAG, ITS scoring, search strategies.
- `docs/01-architecture.md`: fixed test count (229→239), search description (sqlite-vec→MIB), removed phantom `api_keys` table.
- `docs/02-mcp-tools.md`: added `sources` parameter to `memory_search_rrf`.
- `docs/04-rag.md`: added `thresholds`/`search_strategy` params to RAGEngine, deprecation notices for `search_rrf`/`search_binary`, MultiSourceRAG section, `keep_float_blobs` config.
- `docs/07-hooks.md`: clarified `_importance_gate` is called directly, not via hook registry.
- `docs/09-features.md`: added `features/secrets.py` documentation.
- `README_EN.md`: fixed test count (237→239), synced rag config block.
- `README.md`: synced doc 04 description with README_EN.

---

## [0.x] - 2026-06-21 to 2026-06-28

### Features (highlights)
- **Unified 19-tool API** — single `layer` parameter instead of 37 separate tools.
- **RAG unified search facade** — `search(query, strategy)` with 4 strategies: `fts`, `mib`, `hybrid`, `auto`.
- **MIB binary embeddings** — 384 dims → 48 bytes via Maximally-Informative Binarization.
- **Supervised threshold training** — per-dimension MIB thresholds from labeled pairs (+10-15% recall).
- **ITS-inspired novelty scoring** — document frequency as prior for retrieval surprise.
- **MultiSourceRAG** — unified RAG + Wiki search with dedup and reranking.
- **Envelope encryption** — API keys/bearer tokens encrypted at rest with libsodium secretbox.
- **Saga pattern** — multi-step operations with compensation, watchdog, nested sagas, per-step timeouts.
- **Knowledge graphs** — epistemic (facts/decisions) + temporal (timeline) via recursive CTE.
- **Wiki system** — 14 content types, .md source of truth, external folder sync.
- **24 hooks** — intercept memory operations at every stage.
- **Platform-aware async** — aiosqlite on Linux/macOS, sync fallback on Windows.
- **Rate limiting** — all MCP tools, WebSocket/SSE, HTTP API endpoints.
- **Read-only replica** mode.
- **Connection pooling** — `AsyncConnectionManager` with WAL mode.
- **Import/export** — `memory_export`/`memory_import`/`memory_list_exports` tools.
- **Lucidity purge** — context injection, lucidity scoring.
- **Embedding cache** — avoid redundant inference calls.
- **Memory compression** — context-mode integration.
- **Archived memories** — soft delete with `ArchivedMemories`.
- **Emotion trigger** — emotion detection in memory operations.
- **RetrievalRouter** — multi-signal query routing with entity/NER extraction.

### Infrastructure
- CI matrix: Python 3.10–3.13, lint + test jobs.
- npm wrapper (`mcp-ariel-memory@1.0.0`) for `npx` deployment.
- Docker support with `docker-compose.yml`.
- MCP Registry published as `io.github.Cipher208/ariel-memory@1.0.0`.
- ruff check + ruff format enforced.
- 239 tests across 22 test files.

### Documentation
- 14 doc files covering architecture, tools, core, RAG, graph, lifecycle, hooks, wiki, features, shared, operations, testing.
- English README + Russian README.
- Architecture diagrams in `docs/01-architecture.md`.
- Full MCP tools reference in `docs/02-mcp-tools.md`.
