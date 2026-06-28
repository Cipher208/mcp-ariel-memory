# Operations

## Transports

### stdio

```bash
python -m mcp_ariel_memory --transport stdio
```

### Streamable HTTP (recommended)

```bash
python -m mcp_ariel_memory --transport http --port 8000
```

> **Streamable HTTP** — new in MCP SDK v1.28 (not SSE). POST/DELETE for requests, GET for SSE stream. Stateless mode, load balancer friendly.

### HTTP + Dashboard + Metrics

```bash
python -m mcp_ariel_memory --transport http --port 8000 --dashboard
```

## Dashboard + Auth + Rate Limiting

**All endpoints are protected:** auth (Bearer token) + rate limit (100 req/min) + WS connection limit (5 per user, 100 total).

| Endpoint | Auth | Rate Limit |
|----------|------|------------|
| `/dashboard` | ✅ | ✅ |
| `/api/stats` | ✅ | ✅ |
| `/api/user/facts` | ✅ | ✅ |
| `/api/agent/facts` | ✅ | ✅ |
| `/api/user/episodes` | ✅ | ✅ |
| `/api/agent/episodes` | ✅ | ✅ |
| `/api/audit` | ✅ | ✅ |
| `/api/auth/keys` | ✅ | ✅ |
| `/api/auth/create` | ✅ | ✅ |
| `/api/backup/trigger` | ✅ | ✅ |
| `/api/backup/list` | ✅ | ✅ |
| `/metrics` | ✅ | ✅ |
| `/metrics/json` | ✅ | ✅ |
| `/mcp` (WebSocket) | — | ✅ (connection limit) |

## OpenAPI

Specification: `openapi.yaml` (OpenAPI 3.1.0).

```bash
# View in Swagger UI
npx swagger-ui-serve openapi.yaml
```

## Configuration (config.yaml)

```yaml
layers:
  user: { enabled: true }
  agent: { enabled: true }

limits: { l1_buffer_size: 50, l4_core_limit: 5000 }

hooks:
  user: { message_received: true, emotion_trigger: true }
  agent: { error_occurred: true, decision_made: true }

forgetting: { decay_rate: 0.01, archive_threshold_days: 90 }
rag: { fts_enabled: true, vec_enabled: true }
embeddings: { model: "intfloat/multilingual-e5-small", dimension: 384 }
graph: { temporal_enabled: true, epistemic_enabled: true, max_depth: 3 }

wiki:
  user: { diary: true, external_dirs: [] }
  agent: { decision_log: true, external_dirs: [] }

auth: { api_keys_enabled: true, bearer_token_enabled: true }

backup:
  auto_backup: true
  backup_interval_hours: 24
  backup_retention_days: 30
  jitter_seconds: 3600
  wiki_sync_interval_minutes: 30

security:
  rate_limit_per_user: 100
  max_ws_per_user: 5
  max_ws_total: 100
```
