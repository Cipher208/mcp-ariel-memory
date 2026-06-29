# Architecture

## Tech Stack

| Component | Technology |
|-----------|-----------|
| MCP protocol | Python MCP SDK v1.28 (FastMCP) |
| Transports | stdio + Streamable HTTP |
| Storage | **Single `memory.db` file** (~21 tables) |
| Async DB | asyncio + sqlite3 via to_thread |
| Search | FTS5 + sqlite-vec (optional) + RRF |
| Hooks | 24 hooks, integrated into tool pipeline |
| Docker | Dockerfile + docker-compose |
| Tests | pytest + pytest-asyncio (171 tests) |
| CI/CD | GitHub Actions |

## Two-Layer Model

```
┌─────────────────────────────────────────────────────┐
│               MCP Server (19 async tools)            │
│  FastMCP + stdio/HTTP transports + auth              │
├──────────────────────┬──────────────────────────────┤
│   Layer 1: User      │   Layer 2: Agent             │
│   User facts         │   Agent identity             │
├──────────────────────┼──────────────────────────────┤
│ L1 ReflexBuffer      │ L1 AgentBuffer               │
│ L2 SessionStore      │ L2 AgentSession              │
│ L3 EpisodicMemory    │ L3 AgentEpisodic             │
│ L4 CoreMemory        │ L4 AgentCore                 │
│ RAG (wiki user)      │ RAG (wiki agent)             │
│ Graph (user)         │ Graph (agent + tags)         │
│ Hooks (user events)  │ Hooks (agent events)         │
├──────────────────────┴──────────────────────────────┤
│ Features: Auth | Backup | Dashboard | Metrics       │
│ Shared: Cache | DB Pool | Embeddings                │
└─────────────────────────────────────────────────────┘
```

## Memory Hierarchy L1 → L4

| Level | Purpose | Storage | Limit |
|-------|---------|---------|-------|
| **L1 ReflexBuffer** | Recent messages (ring buffer) | RAM + JSON | 50 |
| **L2 SessionStore** | Session history with indexes | SQLite | 100 |
| **L3 EpisodicMemory** | Important moments with emotional weight | SQLite | 1000 |
| **L4 CoreMemory** | Key-value facts with importance | SQLite | 5000 |

## Consolidation

```
Message → L1 (buffer)
         → ImportanceGate (noise filter, threshold 0.3)
         → L2 (session)
         → EmotionTrigger (emotional analysis)
         → L3 (episodes, if importance > 0.7)
         → L4 (consolidation, if weight > 0.7)
```

## Database Tables (21)

| Table | Module | Purpose |
|-------|--------|---------|
| `core_memory` | core/memory.py | L4 key-value facts |
| `sessions` | core/session.py | L2 session history |
| `episodes` | core/episodic.py | L3 episodic memories |
| `staging_memories` | shared/dream_buffer.py | Temporary staging |
| `archived_memories` | shared/archived_memories.py | Archived memories |
| `audit_log` | features/audit_trail.py | Audit trail |
| `rate_limits` | features/rate_limiting.py | Rate limiting |
| `embedding_cache` | shared/embeddings.py | Cached embeddings |
| `rag_pages` | rag/engine.py | RAG document pages |
| `rag_chunks` | rag/engine.py | RAG document chunks |
| `rag_relations` | rag/engine.py | RAG relations |
| `epi_nodes` | graph/epistemic.py | Epistemic graph nodes |
| `epi_edges` | graph/epistemic.py | Epistemic graph edges |
| `temporal_events` | graph/temporal.py | Temporal events |
| `temporal_links` | graph/temporal.py | Temporal links |
| `user_wiki` | wiki/user_wiki.py | User wiki entries |
| `agent_wiki` | wiki/agent_wiki.py | Agent wiki entries |
| `wiki_index` | wiki/file_wiki.py | Wiki FTS5 index |
| `memory_conflicts` | rag/conflict.py | Memory conflicts |
| `migration_log` | shared/migrations.py | Migration history |
| `api_keys` | features/auth.py | API keys |
