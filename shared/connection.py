"""
AsyncConnectionManager — unified SQLite connection manager.

Rules:
- One connection per DB file (no pool — connection pooling is an anti-pattern for SQLite)
- WAL + busy_timeout for concurrency
- Native async via aiosqlite (already in dependencies)
- row_factory = aiosqlite.Row (compatible with sqlite3.Row)

Usage:
    cm = AsyncConnectionManager()
    conn = await cm.get("memory.db")
    cur = await conn.execute("SELECT * FROM users WHERE id=?", (uid,))
    row = await cur.fetchone()
"""

import os
import logging
from pathlib import Path
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)

_DEFAULT_DIR = os.environ.get(
    "MCP_MEMORY_DATA_DIR",
    str(Path.home() / ".mcp-ariel-memory"),
)


class AsyncConnectionManager:
    """One connection per DB file. No pool — internal queue in aiosqlite."""

    def __init__(self, base_dir: str = ""):
        self.base_dir = Path(base_dir or _DEFAULT_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._conns: dict[str, aiosqlite.Connection] = {}

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    async def get(self, db_name: str = "memory.db") -> aiosqlite.Connection:
        """Return (or create) a connection to `db_name`."""
        if db_name in self._conns:
            conn = self._conns[db_name]
            # check if connection is alive
            try:
                await conn.execute("SELECT 1")
                return conn
            except Exception:
                logger.warning("connection %s stale, reopening", db_name)
                del self._conns[db_name]

        db_path = str(self.base_dir / db_name)
        conn = await aiosqlite.connect(db_path)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA busy_timeout=5000")
        await conn.execute("PRAGMA synchronous=NORMAL")
        # foreign keys for integrity
        await conn.execute("PRAGMA foreign_keys=ON")

        self._conns[db_name] = conn
        logger.debug("opened connection %s (%s)", db_name, db_path)
        return conn

    async def close_all(self):
        """Close all open connections (on shutdown)."""
        for name, conn in self._conns.items():
            try:
                await conn.close()
                logger.debug("closed connection %s", name)
            except Exception:
                pass
        self._conns.clear()

    def stats(self) -> dict:
        return {
            "connections": len(self._conns),
            "dbs": list(self._conns.keys()),
        }

    # ------------------------------------------------------------------
    # Helpers for migrations and init-db
    # ------------------------------------------------------------------

    async def execute_script(self, db_name: str, script: str):
        """Execute a SQL script (e.g. CREATE TABLE) and commit."""
        conn = await self.get(db_name)
        await conn.executescript(script)
        await conn.commit()

    async def table_exists(self, db_name: str, table: str) -> bool:
        """Check whether a table exists."""
        conn = await self.get(db_name)
        cur = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        )
        row = await cur.fetchone()
        return row is not None

    async def vacuum(self, db_name: str):
        """VACUUM — reclaim space after bulk deletions."""
        conn = await self.get(db_name)
        await conn.execute("VACUUM")
        await conn.commit()


# Global instance — used by default
connection_manager = AsyncConnectionManager()


# ------------------------------------------------------------------
# Example: how to migrate any module to AsyncConnectionManager
# ------------------------------------------------------------------
#
# BEFORE:
#
#   class CoreMemory:
#       def __init__(self, db_path=None):
#           self.db_path = db_path or str(Path.home() / ".mcp-ariel-memory" / "memory.db")
#           self._init_db()
#
#       def _get_conn(self):
#           conn = sqlite3.connect(self.db_path)
#           conn.row_factory = sqlite3.Row
#           conn.execute("PRAGMA journal_mode=WAL")
#           return conn
#
# AFTER:
#
#   class CoreMemory:
#       def __init__(self, cm: AsyncConnectionManager = None):
#           self._cm = cm or connection_manager
#
#       async def _init_db(self):
#           await self._cm.execute_script("memory.db", """
#               CREATE TABLE IF NOT EXISTS core_memory (...)
#           """)
#
#       async def save(self, user_id, key, value, importance=0.5):
#           conn = await self._cm.get("memory.db")
#           await conn.execute("UPSERT ...", (user_id, key, value, importance))
#           await conn.commit()