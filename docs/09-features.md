# Фичи — features/

## Auth (`features/auth.py`)

### API Keys

```python
from features.auth import APIKeyAuth

auth = APIKeyAuth()
key = auth.create_key("alice", "my key")
auth.verify(key)       # {"user_id": "alice", "label": "my key"}
auth.revoke(key)       # True
auth.list_keys()       # [{"key": "ak_e9eb...", ...}]
auth.delete_key(key)   # True
```

### Bearer Token

```python
from features.auth import BearerAuth

bearer = BearerAuth()
token = bearer.get_token()     # "mt_..."
bearer.verify("Bearer mt_...")  # True
```

## Backup (`features/backup.py`)

```python
from features.backup import BackupManager

bm = BackupManager()
path = bm.backup("pre_migration")
bm.restore("pre_migration")
bm.list_backups()
bm.cleanup_old()
```

## BackupCron (`features/backup_cron.py`)

Автобэкап каждые 24 часа (включён по умолчанию).

```python
from features.backup_cron import backup_cron

backup_cron.start()        # запустить cron
backup_cron.stop()         # остановить
backup_cron.backup_now()   # немедленный бэкап
backup_cron.list_backups()
backup_cron.restore("auto_1782041841")
backup_cron.status()       # {"running": True, "interval_hours": 24, ...}
```

## Dashboard (`features/dashboard.py`)

HTML дашборд для визуализации памяти.

```python
from features.dashboard import Dashboard

d = Dashboard()
d.get_stats("alice")         # {"l1_buffer": 0, "l4_facts": 45, ...}
d.get_user_facts("alice")    # [{"key": "name", "value": "Alice", ...}]
d.get_agent_facts("alice")
d.get_user_episodes("alice")
d.get_agent_episodes("alice")
d.get_audit()
d.render_html()              # HTML строка
```

## AuditTrail (`features/audit_trail.py`)

Лог всех изменений с auto-rotation (30 дней).

```python
from features.audit_trail import AuditTrail

at = AuditTrail()
at.log("alice", "memory.user.remember", layer="user", details={"key": "name"})
at.get_history("alice", limit=50)
at.get_history("alice", action="memory.user.remember")
at.count("alice")
at.count_all()

# Ротация: архивировать > 30 дней в JSON, затем удалить
at.archive_and_prune(retention_days=30, archive_dir="/path/to/archives")
# {"archived": 100, "pruned": 100}

# Просто удалить старые
at.cleanup_old(retention_days=30)
```

## RateLimiter (`features/rate_limiting.py`)

Ограничение API вызовов per user (100/мин). SQLite-based — переживает рестарт.

```python
from features.rate_limiting import RateLimiter

rl = RateLimiter()
rl.check("alice")       # {"allowed": True, "remaining": 99}
rl.get_stats("alice")   # {"requests_last_minute": 1, "limit": 100}
rl.cleanup_old()        # удалить старые записи
```

## ImportExport (`features/import_export.py`)

```python
from features.import_export import ImportExport

ie = ImportExport()
path = ie.export_user("alice")
ie.import_user(path, target_user_id="bob")
ie.list_exports()
```

## Compression (`features/compression.py`)

```python
from features.compression import MemoryCompressor

mc = MemoryCompressor()
mc.deduplicate_core("alice")
mc.compress_episodes("alice", min_weight=0.3)
mc.get_stats("alice")
```
