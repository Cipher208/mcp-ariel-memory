# Changelog

## v1.0.0 (2026-07-01)

### Features
- 19 unified MCP tools with layer parameter
- 4-layer memory architecture (L1-L4)
- Typed memory (13 categories)
- RAG search (FTS5 + MIB + hybrid)
- Knowledge graphs (epistemic + temporal)
- Wiki system (14 content types)
- Saga pattern (retry, idempotency, compensation)
- Envelope encryption (libsodium)
- Platform-aware async (aiosqlite / asyncio.to_thread)
- 24 hooks with importance gating
- Automatic backups with jitter
- Rate limiting
- Dashboard
- Health endpoints

### Testing
- 338 tests passing
- 25 property-based Hypothesis tests
- CI on Python 3.10-3.13
- Type checking (mypy)
- Linting (ruff)
- Secret scanning (gitleaks)
