"""
L4 CoreMemory — async key-value facts with importance
"""

import time
from dataclasses import dataclass

from shared.connection import AsyncConnectionManager, connection_manager


@dataclass
class CoreEntry:
    entry_id: int
    user_id: str
    key: str
    value: str
    importance: float
    created_at: float
    updated_at: float


class CoreMemory:
    def __init__(self, cm: AsyncConnectionManager | None = None):
        self._cm = cm or connection_manager

    async def _init_db(self):
        await self._cm.execute_script(
            "memory.db",
            """
            CREATE TABLE IF NOT EXISTS core_memory (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL,
                importance REAL DEFAULT 0.5, created_at REAL NOT NULL, updated_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_core_user ON core_memory(user_id);
            CREATE INDEX IF NOT EXISTS idx_core_key ON core_memory(key);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_core_user_key ON core_memory(user_id, key);
        """,
        )

    async def save(self, user_id: str, key: str, value: str, importance: float = 0.5) -> int:
        now = time.time()
        conn = await self._cm.get("memory.db")
        cursor = await conn.execute(
            "SELECT entry_id FROM core_memory WHERE user_id=? AND key=?",
            (user_id, key),
        )
        existing = await cursor.fetchone()
        if existing:
            await conn.execute(
                "UPDATE core_memory SET value=?, importance=?, updated_at=? WHERE entry_id=?",
                (value, importance, now, existing["entry_id"]),
            )
            entry_id = existing["entry_id"]
        else:
            cursor = await conn.execute(
                "INSERT INTO core_memory (user_id, key, value, importance, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, key, value, importance, now, now),
            )
            entry_id = cursor.lastrowid
        await conn.commit()
        return entry_id

    async def get(self, user_id: str, key: str) -> CoreEntry | None:
        """Get a fact by key. Returns None if not found."""
        conn = await self._cm.get("memory.db")
        cursor = await conn.execute("SELECT * FROM core_memory WHERE user_id=? AND key=?", (user_id, key))
        row = await cursor.fetchone()
        return self._row_to_entry(row) if row else None

    async def get_or_default(self, user_id: str, key: str, default: str = "") -> str:
        """Get value or return default (never returns None)."""
        entry = await self.get(user_id, key)
        return entry.value if entry else default

    async def get_all(self, user_id: str, limit: int = 50) -> list[CoreEntry]:
        conn = await self._cm.get("memory.db")
        cursor = await conn.execute(
            "SELECT * FROM core_memory WHERE user_id=? ORDER BY importance DESC LIMIT ?", (user_id, limit)
        )
        rows = await cursor.fetchall()
        return [self._row_to_entry(r) for r in rows]

    async def delete(self, user_id: str, key: str) -> bool:
        conn = await self._cm.get("memory.db")
        cursor = await conn.execute("DELETE FROM core_memory WHERE user_id=? AND key=?", (user_id, key))
        await conn.commit()
        return cursor.rowcount > 0

    async def search(self, user_id: str, query: str, limit: int = 10) -> list[dict]:
        conn = await self._cm.get("memory.db")
        cursor = await conn.execute(
            "SELECT * FROM core_memory WHERE user_id=? AND (key LIKE ? OR value LIKE ?) ORDER BY importance DESC LIMIT ?",
            (user_id, f"%{query}%", f"%{query}%", limit),
        )
        rows = await cursor.fetchall()
        return [{"key": r["key"], "value": r["value"], "importance": r["importance"]} for r in rows]

    async def count(self, user_id: str | None = None) -> int:
        conn = await self._cm.get("memory.db")
        if user_id:
            cursor = await conn.execute("SELECT COUNT(*) FROM core_memory WHERE user_id=?", (user_id,))
        else:
            cursor = await conn.execute("SELECT COUNT(*) FROM core_memory")
        row = await cursor.fetchone()
        return row[0] if row else 0

    def _row_to_entry(self, row) -> CoreEntry:
        return CoreEntry(
            entry_id=row["entry_id"],
            user_id=row["user_id"],
            key=row["key"],
            value=row["value"],
            importance=row["importance"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
