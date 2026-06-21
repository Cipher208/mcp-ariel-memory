# Операции

## Транспорты

### stdio (Claude Desktop / Codex / Cursor)

```bash
python -m mcp_ariel_memory --transport stdio
```

### Streamable HTTP (веб-клиенты, рекомендуется)

```bash
python -m mcp_ariel_memory --transport http --port 8000
```

> **Streamable HTTP** — новый транспорт MCP SDK v1.28 (не SSE). Отличия:
> - POST/DELETE для запросов, GET для SSE stream
> - Stateless режим (`stateless_http=True`)
> - Лучшая масштабируемость (load balancer friendly)
> - JSON ответы (`json_response=True`)

### HTTP + Dashboard + Metrics

```bash
python -m mcp_ariel_memory --transport http --port 8000 --dashboard
```

## Dashboard (при `--dashboard`)

| URL | Описание |
|-----|----------|
| `/dashboard` | HTML дашборд (требует Bearer token) |
| `/api/stats` | JSON статистика |
| `/api/user/facts` | User L4 facts |
| `/api/agent/facts` | Agent L4 facts |
| `/api/user/episodes` | User episodes |
| `/api/agent/episodes` | Agent episodes |
| `/api/audit` | Audit log |
| `/api/auth/keys` | API keys |
| `/api/backup/list` | Backups |

### Metrics (Prometheus)

```bash
curl http://localhost:8000/metrics        # Prometheus
curl http://localhost:8000/metrics/json   # JSON
```

| Метрика | Тип | Описание |
|---------|-----|----------|
| `ariel_memory_uptime_seconds` | gauge | Время работы |
| `ariel_memory_tool_calls` | counter | Всего вызовов |
| `ariel_memory_tool_*` | counter | Вызовы по tool |
| `ariel_memory_latency_*` | histogram | Латентность |

## Аутентификация

### API Keys

```bash
curl -X POST http://localhost:8000/api/auth/create \
  -H "Content-Type: application/json" \
  -d '{"user_id": "alice", "label": "my key"}'

curl http://localhost:8000/api/auth/keys
```

### Bearer Token

```bash
curl -H "Authorization: Bearer mt_..." http://localhost:8000/api/stats
```

### Отключение auth (для dev)

```yaml
auth:
  bearer_token_enabled: false
```

## Backup Cron

Автобэкап каждые 24 часа.

```bash
curl -X POST http://localhost:8000/api/backup/trigger
curl http://localhost:8000/api/backup/list
```

## Конфигурация (config.yaml)

```yaml
layers:
  user: { enabled: true }
  agent: { enabled: true }

limits:
  l1_buffer_size: 50
  l2_session_limit: 100
  l3_episodic_limit: 1000
  l4_core_limit: 5000

hooks:
  user: { message_received: true, emotion_trigger: true, ... }
  agent: { error_occurred: true, decision_made: true, ... }

forgetting:
  decay_rate: 0.01
  archive_threshold_days: 90
  archive_min_importance: 0.3

rag: { fts_enabled: true, vec_enabled: true, chunk_size: 500 }

embeddings:
  model: "intfloat/multilingual-e5-small"
  dimension: 384
  fallback: "hash"

graph:
  temporal_enabled: true
  epistemic_enabled: true
  max_depth: 3

wiki:
  user: { diary: true, ..., external_dirs: ["/path/to/notes"] }
  agent: { decision_log: true, ..., external_dirs: ["/path/to/lore"] }

auth:
  api_keys_enabled: true
  bearer_token_enabled: true

backup:
  auto_backup: true
  backup_interval_hours: 24
  backup_retention_days: 30
  jitter_seconds: 3600
  wiki_sync_interval_minutes: 30

security:
  per_user_isolation: true
  rate_limit_per_user: 100
```
