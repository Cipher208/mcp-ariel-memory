# Connection Manager

## Overview

`AsyncConnectionManager` provides unified async SQLite access across platforms.

```python
from shared.connection import connection_manager

# Get a connection (creates if needed)
conn = await connection_manager.get("memory.db")

# Execute queries
cur = await conn.execute("SELECT * FROM memory_entries WHERE user_id=?", ("u1",))
rows = await cur.fetchall()

# Commit
await conn.commit()
```

## Platform Behavior

| Platform | Backend | Event Loop |
|----------|---------|------------|
| Linux/macOS | aiosqlite | True async |
| Windows | sqlite3 + to_thread | Offloaded to thread pool |

## PRAGMA Settings

```sql
PRAGMA journal_mode=WAL
PRAGMA busy_timeout=5000
PRAGMA synchronous=NORMAL
PRAGMA foreign_keys=ON
PRAGMA cache_size=-64000  -- 64MB
PRAGMA temp_store=MEMORY
```

## Connection Lifecycle

1. First `get()` creates connection with PRAGMAs
2. Subsequent `get()` returns cached connection
3. Stale connections (failed ping) are reopened
4. `close_all()` closes all connections on shutdown
