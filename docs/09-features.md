# Фичи — features/

## Auth (`features/auth.py`)

### API Keys

```python
from features.auth import APIKeyAuth
auth = APIKeyAuth()
key = auth.create_key("alice", "my key")
auth.verify(key)
```

### Bearer Token (persistent)

```python
from features.auth import BearerAuth
ba = BearerAuth()
token = ba.get_token()
ba.rotate()
```

## BackupCron (`features/backup_cron.py`)

```python
from features.backup_cron import backup_cron
backup_cron.start()
await backup_cron.backup_now()
backup_cron.status()
```

## Dashboard (`features/dashboard.py`)

```python
from features.dashboard import Dashboard
d = Dashboard()
stats = await d.get_stats("alice")
facts = await d.get_user_facts("alice")
```

## AuditTrail (`features/audit_trail.py`) — async

```python
from features.audit_trail import AuditTrail
at = AuditTrail()
await at.log("alice", "action")
history = await at.get_history("alice")
await at.archive_and_prune(retention_days=30)
await at.cleanup_old(retention_days=30)
```

## RateLimiter (`features/rate_limiting.py`) — async

```python
from features.rate_limiting import RateLimiter, ConnectionLimiter

rl = RateLimiter()
result = await rl.check("alice")
stats = await rl.get_stats("alice")

cl = ConnectionLimiter()
cl.acquire("alice", "conn_1")
cl.release("alice", "conn_1")
```

## ImportExport + Compression — async

```python
from features.import_export import ImportExport
from features.compression import MemoryCompressor

ie = ImportExport()
path = await ie.export_user("alice")

mc = MemoryCompressor()
await mc.deduplicate_core("alice")
```

### Bearer Token (persistent)

Токен сохраняется в файл, переживает рестарт.

```python
from features.auth import BearerAuth
ba = BearerAuth()
token = ba.get_token()      # один и тот же после рестартов
ba.verify("Bearer mt_...")  # True
new_token = ba.rotate()     # ротация (старый перестаёт работать)
```

**Файл:** `~/.mcp-ariel-memory/bearer_token.json`

## BackupCron (`features/backup_cron.py`)

Автобэкап с jitter + авто-синхронизация wiki.

```python
from features.backup_cron import backup_cron
backup_cron.start()
backup_cron.backup_now()
backup_cron.status()
# {"interval_hours": 24, "jitter_seconds": 3600, "wiki_sync_interval_minutes": 30, ...}
```

**Jitter:** случайная задержка 0-3600 сек → серверы не бэкапятся одновременно.
**Wiki sync:** переиндексация .md файлов каждые 30 минут.

## Dashboard (`features/dashboard.py`)

```python
from features.dashboard import Dashboard
d = Dashboard()
d.get_stats("alice")
d.get_user_facts("alice")
d.render_html()
```

**Эндпоинты (с auth + rate limit):** `/dashboard`, `/api/stats`, `/api/user/facts`, `/api/agent/facts`, `/api/user/episodes`, `/api/agent/episodes`, `/api/audit`

## AuditTrail (`features/audit_trail.py`)

Ротация: архивировать > 30 дней в JSON, затем удалить.

```python
from features.audit_trail import AuditTrail
at = AuditTrail()
at.log("alice", "action")
at.get_history("alice")
at.archive_and_prune(retention_days=30)  # {"archived": 100, "pruned": 100}
at.cleanup_old(retention_days=30)
```

## RateLimiter (`features/rate_limiting.py`)

SQLite-based HTTP rate limiting + WebSocket connection limiting.

```python
from features.rate_limiting import RateLimiter, ConnectionLimiter

rl = RateLimiter()
rl.check("alice")       # {"allowed": True, "remaining": 99}

cl = ConnectionLimiter()
cl.acquire("alice", "conn_1")  # {"allowed": True, "user_connections": 1}
cl.release("alice", "conn_1")
cl.get_stats()                  # {"total_connections": 5, "max_per_user": 5}
```

**Защита:** все HTTP endpoints + WebSocket upgrade на `/mcp`.

## ImportExport + Compression

```python
from features.import_export import ImportExport
from features.compression import MemoryCompressor

ie = ImportExport()
path = ie.export_user("alice")

mc = MemoryCompressor()
mc.deduplicate_core("alice")
```
