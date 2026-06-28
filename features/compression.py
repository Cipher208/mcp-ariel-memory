"""
MemoryCompressor — async dedup and compression
"""

import time
from typing import Optional

from shared.connection import AsyncConnectionManager, connection_manager


class MemoryCompressor:
    def __init__(self, cm: Optional["AsyncConnectionManager"] = None):
        self._cm = cm or connection_manager

    async def deduplicate_core(self, user_id: str) -> int:
        conn = await self._cm.get("memory.db")
        cursor = await conn.execute(
            "SELECT user_id, key, COUNT(*) as cnt FROM core_memory WHERE user_id=? GROUP BY user_id, key HAVING cnt > 1",
            (user_id,),
        )
        duplicates = await cursor.fetchall()
        removed = 0
        for dup in duplicates:
            cursor = await conn.execute(
                """DELETE FROM core_memory WHERE user_id=? AND key=? AND entry_id NOT IN
                   (SELECT entry_id FROM core_memory WHERE user_id=? AND key=? ORDER BY updated_at DESC LIMIT 1)""",
                (dup["user_id"], dup["key"], dup["user_id"], dup["key"]),
            )
            removed += cursor.rowcount
        await conn.commit()
        return removed

    async def compress_episodes(self, user_id: str, min_weight: float = 0.3) -> int:
        conn = await self._cm.get("memory.db")
        cutoff = time.time() - 30 * 86400
        cursor = await conn.execute(
            "DELETE FROM episodes WHERE user_id=? AND emotional_weight < ? AND created_at < ?",
            (user_id, min_weight, cutoff),
        )
        await conn.commit()
        return cursor.rowcount

    async def get_stats(self, user_id: str = None) -> dict[str, int]:
        stats = {}
        for name, db in [("core", "memory.db"), ("episodes", "memory.db"), ("sessions", "memory.db")]:
            conn = await self._cm.get(db)
            tables = [r[0] for r in await (await conn.execute("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()]
            total = 0
            for t in tables:
                try:
                    row = await (await conn.execute("SELECT COUNT(*) FROM %s" % t)).fetchone()
                    total += row[0] if row else 0
                except Exception:
                    pass
            stats[name] = total
        return stats
