# Features — features/

## Auth (`features/auth.py`)

### APIKeyAuth

API key authentication with encrypted file persistence. Keys are stored in `~/.mcp-ariel-memory/api_keys.json` and encrypted at rest using libsodium secretbox (AES-256-GCM). Legacy plain JSON files are auto-rotated to encrypted format on first read.

#### Class: `APIKeyAuth`

```python
class APIKeyAuth:
    def __init__(self, keys_file: str = None)
```

**Description**: Creates an APIKeyAuth instance. Loads existing keys from file if present.

**Parameters**:
- `keys_file` (str, optional): Path to the keys file. Defaults to `~/.mcp-ariel-memory/api_keys.json`.

**Attributes**:
- `keys_file` (Path): Path to the keys storage file.
- `_keys` (Dict[str, Dict]): Internal mapping of keys to metadata.

---

#### `APIKeyAuth.create_key(user_id: str, label: str = "") -> str`

**Description**: Create a new API key for a user.

**Parameters**:
- `user_id` (str): The user ID to associate with the key.
- `label` (str, optional): A human-readable label for the key. Defaults to `""`.

**Returns**: `str` — the generated API key (format: `ak_{48 hex chars}`).

**Example**:
```python
from features.auth import APIKeyAuth

auth = APIKeyAuth()
key = auth.create_key("alice", "my key")
print(key)
# "ak_a1b2c3d4e5f6..."
```

---

#### `APIKeyAuth.verify(key: str) -> Optional[Dict[str, Any]]`

**Description**: Verify an API key and update last_used timestamp.

**Parameters**:
- `key` (str): The API key to verify.

**Returns**: `Optional[Dict[str, Any]]` — `{"user_id": str, "label": str}` if valid, `None` if invalid or disabled.

**Example**:
```python
result = auth.verify("ak_a1b2c3d4e5f6...")
print(result)
# {"user_id": "alice", "label": "my key"}

result = auth.verify("invalid_key")
# None
```

---

#### `APIKeyAuth.revoke(key: str) -> bool`

**Description**: Revoke an API key (soft delete — disables the key).

**Parameters**:
- `key` (str): The API key to revoke.

**Returns**: `bool` — `True` if revoked, `False` if key not found.

**Example**:
```python
success = auth.revoke("ak_a1b2c3d4e5f6...")
print(success)  # True
```

---

#### `APIKeyAuth.list_keys() -> list`

**Description**: List all API keys with metadata (key is truncated for security).

**Parameters**: None

**Returns**: `list` — list of dicts with keys `key`, `user_id`, `label`, `enabled`, `created_at`.

**Example**:
```python
keys = auth.list_keys()
print(keys)
# [{"key": "ak_a1b2c...", "user_id": "alice", "label": "my key", "enabled": True, "created_at": 1234567890.0}]
```

---

#### `APIKeyAuth.delete_key(key: str) -> bool`

**Description**: Permanently delete an API key.

**Parameters**:
- `key` (str): The API key to delete.

**Returns**: `bool` — `True` if deleted, `False` if key not found.

**Example**:
```python
success = auth.delete_key("ak_a1b2c3d4e5f6...")
print(success)  # True
```

---

### BearerAuth

Bearer token authentication — persistent and encrypted. Token survives server restarts, stored encrypted at rest.

#### Class: `BearerAuth`

```python
class BearerAuth:
    def __init__(self, token_file: str = None)
```

**Description**: Creates a BearerAuth instance. Loads or creates token on initialization.

**Parameters**:
- `token_file` (str, optional): Path to the token file. Defaults to `~/.mcp-ariel-memory/bearer_token.json`.

**Attributes**:
- `token_file` (Path): Path to the token storage file.
- `_token` (str): The current bearer token.

**Token Resolution Order**:
1. `MCP_AUTH_TOKEN` environment variable
2. Existing token from file
3. Generate new token (format: `mt_{64 hex chars}`)

---

#### `BearerAuth.verify(auth_header: str) -> bool`

**Description**: Verify a Bearer token from an Authorization header.

**Parameters**:
- `auth_header` (str): The full Authorization header value (e.g., `"Bearer mt_..."`).

**Returns**: `bool` — `True` if valid, `False` otherwise.

**Example**:
```python
from features.auth import BearerAuth

ba = BearerAuth()
token = ba.get_token()

valid = ba.verify(f"Bearer {token}")
print(valid)  # True

valid = ba.verify("Bearer invalid_token")
print(valid)  # False
```

---

#### `BearerAuth.get_token() -> str`

**Description**: Get the current bearer token.

**Parameters**: None

**Returns**: `str` — the current bearer token.

**Example**:
```python
token = ba.get_token()
print(token)  # "mt_a1b2c3d4..."
```

---

#### `BearerAuth.rotate() -> str`

**Description**: Rotate the bearer token. The old token stops working immediately.

**Parameters**: None

**Returns**: `str` — the new bearer token.

**Example**:
```python
new_token = ba.rotate()
print(new_token)  # "mt_e5f6g7h8..."

# Old token no longer works
ba.verify(f"Bearer {old_token}")  # False
```

---

### Singletons

```python
from features.auth import api_key_auth, bearer_auth

# Use pre-configured instances
key = api_key_auth.create_key("alice")
valid = bearer_auth.verify("Bearer mt_...")
```

---

## BackupManager (`features/backup.py`)

Async backup/restore of all databases.

### Class: `BackupManager`

```python
class BackupManager:
    def __init__(self, base_dir: str = None)
```

**Description**: Creates a BackupManager instance.

**Parameters**:
- `base_dir` (str, optional): Base directory for memory data. Defaults to `~/.mcp-ariel-memory`.

**Attributes**:
- `base_dir` (Path): Base directory path.
- `backup_dir` (Path): Backup directory path (`base_dir/backups`).

---

### `BackupManager.backup(label: str = None) -> str`

**Description**: Create a backup of all database files.

**Parameters**:
- `label` (str, optional): Custom backup name. If None, generates `backup_{timestamp}_{uuid}`.

**Returns**: `str` — path to the backup directory.

**Example**:
```python
from features.backup import BackupManager

bm = BackupManager()
path = await bm.backup("pre-upgrade")
print(path)  # "/home/user/.mcp-ariel-memory/backups/pre-upgrade"
```

---

### `BackupManager.restore(backup_name: str) -> Dict[str, Any]`

**Description**: Restore databases from a backup.

**Parameters**:
- `backup_name` (str): Name of the backup to restore.

**Returns**: `Dict[str, Any]` — `{"restored": List[str], "backup": str}` or `{"error": str}`.

**Example**:
```python
result = await bm.restore("pre-upgrade")
print(result)
# {"restored": ["memory.db"], "backup": "pre-upgrade"}
```

---

### `BackupManager.list_backups() -> List[Dict[str, Any]]`

**Description**: List all available backups.

**Parameters**: None

**Returns**: `List[Dict[str, Any]]` — list of backup info dicts with `name`, `timestamp`, `files`.

**Example**:
```python
backups = bm.list_backups()
print(backups)
# [{"name": "pre-upgrade", "timestamp": 1234567890, "files": ["memory.db"]}]
```

---

### `BackupManager.cleanup_old() -> int`

**Description**: Remove backups older than retention period (default 30 days).

**Parameters**: None

**Returns**: `int` — number of backups removed.

**Example**:
```python
removed = bm.cleanup_old()
print(f"Removed {removed} old backups")
```

---

## BackupCron (`features/backup_cron.py`)

Automatic scheduled backups with jitter + wiki sync.

### Class: `BackupCron`

```python
class BackupCron:
    def __init__(self, base_dir: str = None)
```

**Description**: Creates a BackupCron instance with configuration from config.yaml.

**Parameters**:
- `base_dir` (str, optional): Base directory for memory data. Defaults to `~/.mcp-ariel-memory`.

**Attributes**:
- `interval_hours` (int): Backup interval in hours (default: 24).
- `retention_days` (int): Backup retention in days (default: 30).
- `jitter_seconds` (int): Random jitter range in seconds (default: 3600).
- `wiki_sync_interval` (int): Wiki sync interval in minutes (default: 30).

---

### `BackupCron.start() -> None`

**Description**: Start the backup cron daemon thread.

**Parameters**: None

**Returns**: None

**Example**:
```python
from features.backup_cron import backup_cron

backup_cron.start()
# "Backup cron started (interval=24h (+3600s jitter))"
```

---

### `BackupCron.stop() -> None`

**Description**: Stop the backup cron daemon thread.

**Parameters**: None

**Returns**: None

**Example**:
```python
backup_cron.stop()
```

---

### `BackupCron.backup_now() -> str`

**Description**: Trigger an immediate backup (bypasses cron schedule).

**Parameters**: None

**Returns**: `str` — path to the created backup.

**Example**:
```python
path = backup_cron.backup_now()
print(path)  # "/home/user/.mcp-ariel-memory/backups/auto_1234567890_a1b2c3"
```

---

### `BackupCron.restore(backup_name: str) -> Dict[str, Any]`

**Description**: Restore from a named backup.

**Parameters**:
- `backup_name` (str): Name of the backup to restore.

**Returns**: `Dict[str, Any]` — `{"restored": List[str], "backup": str}` or `{"error": str}`.

**Example**:
```python
result = backup_cron.restore("auto_1234567890_a1b2c3")
print(result)
# {"restored": ["memory.db", "wiki/"], "backup": "auto_1234567890_a1b2c3"}
```

---

### `BackupCron.list_backups() -> list`

**Description**: List all available backups.

**Parameters**: None

**Returns**: `list` — list of backup info dicts.

**Example**:
```python
backups = backup_cron.list_backups()
print(len(backups))  # 5
```

---

### `BackupCron.status() -> Dict[str, Any]`

**Description**: Get backup cron status.

**Parameters**: None

**Returns**: `Dict[str, Any]` — status dict with keys: `running`, `interval_hours`, `jitter_seconds`, `retention_days`, `wiki_sync_interval_minutes`, `last_backup`, `next_backup`, `backup_count`.

**Example**:
```python
status = backup_cron.status()
print(status)
# {
#   "running": True,
#   "interval_hours": 24,
#   "jitter_seconds": 3600,
#   "retention_days": 30,
#   "wiki_sync_interval_minutes": 30,
#   "last_backup": 1234567890.0,
#   "next_backup": 1234654290.0,
#   "backup_count": 5
# }
```

---

### Singleton

```python
from features.backup_cron import backup_cron

backup_cron.start()
```

---

## Dashboard (`features/dashboard.py`)

HTML dashboard for memory visualization.

### Class: `Dashboard`

```python
class Dashboard:
    def __init__(self, data_dir: str = None)
```

**Description**: Creates a Dashboard instance.

**Parameters**:
- `data_dir` (str, optional): Data directory path. Defaults to `~/.mcp-ariel-memory`.

---

### `Dashboard.get_stats(user_id: str = "default") -> Dict[str, Any]`

**Description**: Get memory statistics for a user.

**Parameters**:
- `user_id` (str, optional): User ID. Defaults to `"default"`.

**Returns**: `Dict[str, Any]` — stats dict with keys: `l1_buffer`, `l2_sessions`, `l3_episodes`, `l4_facts`, `wiki_pages`, `graph_nodes`, `agent_l1`, `agent_l2`, `agent_l3`, `agent_l4`, `agent_wiki`.

**Example**:
```python
from features.dashboard import Dashboard

d = Dashboard()
stats = d.get_stats("alice")
print(stats)
# {
#   "l1_buffer": 15,
#   "l2_sessions": 3,
#   "l3_episodes": 25,
#   "l4_facts": 42,
#   "wiki_pages": 10,
#   "graph_nodes": 30,
#   "agent_l1": 8,
#   "agent_l2": 2,
#   "agent_l3": 15,
#   "agent_l4": 20,
#   "agent_wiki": 5
# }
```

---

### `Dashboard.get_user_facts(user_id: str = "default") -> list`

**Description**: Get user facts for display.

**Parameters**:
- `user_id` (str, optional): User ID. Defaults to `"default"`.

**Returns**: `list` — list of fact dicts with `key`, `value`, `importance`.

**Example**:
```python
facts = d.get_user_facts("alice")
print(facts)
# [{"key": "redis_port", "value": "6379", "importance": 0.8}, ...]
```

---

### `Dashboard.get_agent_facts(user_id: str = "default") -> list`

**Description**: Get agent facts for display.

**Parameters**:
- `user_id` (str, optional): User ID. Defaults to `"default"`.

**Returns**: `list` — list of fact dicts with `key`, `value`, `importance`.

**Example**:
```python
facts = d.get_agent_facts("alice")
print(facts)
# [{"key": "preferred_style", "value": "concise", "importance": 0.7}, ...]
```

---

### `Dashboard.get_user_episodes(user_id: str = "default") -> list`

**Description**: Get user episodes for display.

**Parameters**:
- `user_id` (str, optional): User ID. Defaults to `"default"`.

**Returns**: `list` — list of episode dicts with `summary`, `weight`, `tags`.

**Example**:
```python
episodes = d.get_user_episodes("alice")
print(episodes)
# [{"summary": "Discussed Redis config", "weight": 0.6, "tags": ["redis", "config"]}, ...]
```

---

### `Dashboard.get_agent_episodes(user_id: str = "default") -> list`

**Description**: Get agent episodes for display.

**Parameters**:
- `user_id` (str, optional): User ID. Defaults to `"default"`.

**Returns**: `list` — list of episode dicts with `summary`, `weight`, `tags`.

**Example**:
```python
episodes = d.get_agent_episodes("alice")
print(episodes)
# [{"summary": "Learned new debugging pattern", "weight": 0.7, "tags": ["debugging"]}, ...]
```

---

### `Dashboard.get_audit(limit: int = 20) -> list`

**Description**: Get recent audit log entries.

**Parameters**:
- `limit` (int, optional): Maximum entries to return. Defaults to `20`.

**Returns**: `list` — list of audit entry dicts.

**Example**:
```python
audit = d.get_audit(limit=10)
print(audit)
# [{"action": "remember", "user_id": "alice", "timestamp": 1234567890.0}, ...]
```

---

### `Dashboard.render_html() -> str`

**Description**: Render the HTML dashboard.

**Parameters**: None

**Returns**: `str` — complete HTML document.

**Example**:
```python
html = d.render_html()
# Serve this HTML at /dashboard endpoint
```

---

## AuditTrail (`features/audit_trail.py`)

Async, SQLite-based audit logging with rotation.

### Class: `AuditTrail`

```python
class AuditTrail:
    def __init__(self, cm: Optional["AsyncConnectionManager"] = None)
```

**Description**: Creates an AuditTrail instance.

**Parameters**:
- `cm` (Optional[AsyncConnectionManager], optional): Connection manager. Defaults to global `connection_manager`.

---

### `AuditTrail.log(user_id: str, action: str, layer: str = None, target_id: str = None, details: Dict = None) -> None`

**Description**: Log an audit event.

**Parameters**:
- `user_id` (str): The user ID performing the action.
- `action` (str): The action performed (e.g., "remember", "forget", "search").
- `layer` (str, optional): Memory layer affected (e.g., "user", "agent").
- `target_id` (str, optional): ID of the target memory item.
- `details` (Dict, optional): Additional details as key-value pairs.

**Returns**: None

**Example**:
```python
from features.audit_trail import AuditTrail

at = AuditTrail()
await at.log("alice", "remember", layer="user", target_id="fact_123", details={"key": "redis_port"})
```

---

### `AuditTrail.get_history(user_id: str, limit: int = 50, action: str = None) -> List[Dict[str, Any]]`

**Description**: Get audit history for a user.

**Parameters**:
- `user_id` (str): The user ID to query.
- `limit` (int, optional): Maximum entries to return. Defaults to `50`.
- `action` (str, optional): Filter by specific action. Defaults to `None` (all actions).

**Returns**: `List[Dict[str, Any]]` — list of audit entries with `log_id`, `action`, `layer`, `target_id`, `details`, `timestamp`.

**Example**:
```python
history = await at.get_history("alice", limit=10)
print(history)
# [{"log_id": 1, "action": "remember", "layer": "user", "target_id": "fact_123", "details": {...}, "timestamp": 1234567890.0}, ...]

# Filter by action
history = await at.get_history("alice", action="forget")
```

---

### `AuditTrail.count(user_id: str = None) -> int`

**Description**: Count audit log entries.

**Parameters**:
- `user_id` (str, optional): Filter by user ID. Defaults to `None` (all users).

**Returns**: `int` — count of audit entries.

**Example**:
```python
total = await at.count()
user_count = await at.count("alice")
```

---

### `AuditTrail.count_all() -> int`

**Description**: Count all audit log entries (all users).

**Parameters**: None

**Returns**: `int` — total count of audit entries.

**Example**:
```python
total = await at.count_all()
print(f"Total audit entries: {total}")
```

---

### `AuditTrail.cleanup_old(retention_days: int = 30) -> int`

**Description**: Delete audit entries older than retention period.

**Parameters**:
- `retention_days` (int, optional): Retention period in days. Defaults to `30`.

**Returns**: `int` — number of entries deleted.

**Example**:
```python
removed = await at.cleanup_old(retention_days=7)
print(f"Removed {removed} old audit entries")
```

---

### `AuditTrail.archive_and_prune(retention_days: int = 30, archive_dir: str = None) -> Dict[str, int]`

**Description**: Archive old audit entries to JSON, then delete them from database.

**Parameters**:
- `retention_days` (int, optional): Retention period in days. Defaults to `30`.
- `archive_dir` (str, optional): Directory to save archive files. Defaults to `None` (no file archive).

**Returns**: `Dict[str, int]` — `{"archived": int, "pruned": int}`.

**Example**:
```python
result = await at.archive_and_prune(retention_days=30, archive_dir="/tmp/audit_archives")
print(result)
# {"archived": 100, "pruned": 100}
```

---

## RateLimiter (`features/rate_limiting.py`)

Async SQLite-based per-user rate limiting + WebSocket connection limiting.

### Class: `RateLimiter`

```python
class RateLimiter:
    def __init__(self, cm: Optional["AsyncConnectionManager"] = None)
```

**Description**: Creates a RateLimiter instance.

**Parameters**:
- `cm` (Optional[AsyncConnectionManager], optional): Connection manager. Defaults to global `connection_manager`.

**Attributes**:
- `_max_per_user` (int): Max requests per user per window (from config, default: 100).
- `_window_seconds` (int): Rate limit window in seconds (default: 60).

---

### `RateLimiter.check(user_id: str) -> Dict[str, Any]`

**Description**: Check if a user is within rate limits. Records the request.

**Parameters**:
- `user_id` (str): The user ID to check.

**Returns**: `Dict[str, Any]` — 
- `{"allowed": True, "remaining": int}` if within limits
- `{"allowed": False, "remaining": 0, "reset_in": int}` if exceeded

**Example**:
```python
from features.rate_limiting import RateLimiter

rl = RateLimiter()
result = await rl.check("alice")
print(result)
# {"allowed": True, "remaining": 99}

# After many requests...
result = await rl.check("alice")
print(result)
# {"allowed": False, "remaining": 0, "reset_in": 45}
```

---

### `RateLimiter.get_stats(user_id: str) -> Dict[str, Any]`

**Description**: Get rate limit stats for a user.

**Parameters**:
- `user_id` (str): The user ID to query.

**Returns**: `Dict[str, Any]` — `{"requests_last_minute": int, "limit": int}`.

**Example**:
```python
stats = await rl.get_stats("alice")
print(stats)
# {"requests_last_minute": 15, "limit": 100}
```

---

### `RateLimiter.cleanup_old() -> int`

**Description**: Clean up old rate limit entries.

**Parameters**: None

**Returns**: `int` — number of entries removed.

**Example**:
```python
removed = await rl.cleanup_old()
```

---

### Class: `ConnectionLimiter`

```python
class ConnectionLimiter:
    def __init__(self, max_connections_per_user: int = None, max_total: int = None)
```

**Description**: Creates a ConnectionLimiter instance for WebSocket/SSE connections.

**Parameters**:
- `max_connections_per_user` (int, optional): Max connections per user. Defaults to config value or `5`.
- `max_total` (int, optional): Max total connections. Defaults to config value or `100`.

---

### `ConnectionLimiter.acquire(user_id: str, connection_id: str) -> Dict[str, Any]`

**Description**: Acquire a connection slot.

**Parameters**:
- `user_id` (str): The user ID.
- `connection_id` (str): Unique connection identifier.

**Returns**: `Dict[str, Any]` — 
- `{"allowed": True, "user_connections": int, "total_connections": int}` if acquired
- `{"allowed": False, "reason": str, "current": int, "max": int}` if rejected

**Example**:
```python
from features.rate_limiting import ConnectionLimiter

cl = ConnectionLimiter()
result = cl.acquire("alice", "conn_1")
print(result)
# {"allowed": True, "user_connections": 1, "total_connections": 1}

result = cl.acquire("alice", "conn_2")
# ... repeat until limit
result = cl.acquire("alice", "conn_6")
print(result)
# {"allowed": False, "reason": "user_limit", "current": 5, "max": 5}
```

---

### `ConnectionLimiter.release(user_id: str, connection_id: str) -> None`

**Description**: Release a connection slot.

**Parameters**:
- `user_id` (str): The user ID.
- `connection_id` (str): The connection identifier to release.

**Returns**: None

**Example**:
```python
cl.release("alice", "conn_1")
```

---

### `ConnectionLimiter.get_stats() -> Dict[str, Any]`

**Description**: Get connection statistics.

**Parameters**: None

**Returns**: `Dict[str, Any]` — `{"total_connections": int, "max_total": int, "max_per_user": int, "users": Dict[str, int]}`.

**Example**:
```python
stats = cl.get_stats()
print(stats)
# {"total_connections": 5, "max_total": 100, "max_per_user": 5, "users": {"alice": 3, "bob": 2}}
```

---

## ImportExport (`features/import_export.py`)

Async import/export memory between instances.

### Class: `ImportExport`

```python
class ImportExport:
    def __init__(self, cm: Optional["AsyncConnectionManager"] = None)
```

**Description**: Creates an ImportExport instance.

**Parameters**:
- `cm` (Optional[AsyncConnectionManager], optional): Connection manager. Defaults to global `connection_manager`.

**Attributes**:
- `export_dir` (Path): Export directory path (`base_dir/exports`).

---

### `ImportExport.export_user(user_id: str) -> str`

**Description**: Export all memory data for a user to JSON.

**Parameters**:
- `user_id` (str): The user ID to export.

**Returns**: `str` — path to the export file.

**Example**:
```python
from features.import_export import ImportExport

ie = ImportExport()
path = await ie.export_user("alice")
print(path)  # "/home/user/.mcp-ariel-memory/exports/export_alice_1234567890.json"
```

---

### `ImportExport.import_user(filepath: str, target_user_id: str = None) -> Dict[str, int]`

**Description**: Import memory data from a JSON export file.

**Parameters**:
- `filepath` (str): Path to the export file.
- `target_user_id` (str, optional): Target user ID (overrides export's user_id). Defaults to `None`.

**Returns**: `Dict[str, int]` — `{"core_memory": int, "episodes": int}` counts.

**Example**:
```python
result = await ie.import_user("/path/to/export_alice_1234567890.json")
print(result)
# {"core_memory": 42, "episodes": 15}

# Import as different user
result = await ie.import_user("/path/to/export_alice.json", target_user_id="bob")
```

---

### `ImportExport.list_exports() -> List[Dict[str, Any]]`

**Description**: List all export files.

**Parameters**: None

**Returns**: `List[Dict[str, Any]]` — list of export file info with `file` and `size`.

**Example**:
```python
exports = ie.list_exports()
print(exports)
# [{"file": "export_alice_1234567890.json", "size": 15000}, ...]
```

---

## Compression (`features/compression.py`)

Async dedup and compression for memory data.

### Class: `MemoryCompressor`

```python
class MemoryCompressor:
    def __init__(self, cm: Optional["AsyncConnectionManager"] = None)
```

**Description**: Creates a MemoryCompressor instance.

**Parameters**:
- `cm` (Optional[AsyncConnectionManager], optional): Connection manager. Defaults to global `connection_manager`.

---

### `MemoryCompressor.deduplicate_core(user_id: str) -> int`

**Description**: Remove duplicate core memory entries, keeping the most recently updated.

**Parameters**:
- `user_id` (str): The user ID to deduplicate.

**Returns**: `int` — number of duplicate entries removed.

**Example**:
```python
from features.compression import MemoryCompressor

mc = MemoryCompressor()
removed = await mc.deduplicate_core("alice")
print(f"Removed {removed} duplicate entries")
```

---

### `MemoryCompressor.compress_episodes(user_id: str, min_weight: float = 0.3) -> int`

**Description**: Remove old episodes with low emotional weight.

**Parameters**:
- `user_id` (str): The user ID to compress.
- `min_weight` (float, optional): Minimum emotional weight to keep. Defaults to `0.3`.

**Returns**: `int` — number of episodes removed.

**Example**:
```python
removed = await mc.compress_episodes("alice", min_weight=0.5)
print(f"Removed {removed} low-weight episodes")
```

---

### `MemoryCompressor.get_stats(user_id: str = None) -> Dict[str, int]`

**Description**: Get compression statistics.

**Parameters**:
- `user_id` (str, optional): User ID (currently unused). Defaults to `None`.

**Returns**: `Dict[str, int]` — `{"core": int, "episodes": int, "sessions": int}`.

**Example**:
```python
stats = await mc.get_stats()
print(stats)
# {"core": 42, "episodes": 15, "sessions": 8}
```

---

## Configuration

### config.yaml

```yaml
security:
  rate_limit_per_user: 100
  max_ws_per_user: 5
  max_ws_total: 100

backup:
  backup_interval_hours: 24
  backup_retention_days: 30
  jitter_seconds: 3600
  wiki_sync_interval_minutes: 30
```

### File Locations

| File | Path |
|------|------|
| API Keys | `~/.mcp-ariel-memory/api_keys.json` |
| Bearer Token | `~/.mcp-ariel-memory/bearer_token.json` |
| Backups | `~/.mcp-ariel-memory/backups/` |
| Exports | `~/.mcp-ariel-memory/exports/` |
| Audit Archive | Configurable via `archive_dir` |
