"""
Consolidation Engine — L1→L2→L3→L4 memory promotion (async)
Uses CoreMemory.save() instead of duplicating UPSERT logic.
"""
import time
import json
from pathlib import Path
from typing import Dict, Any, List
from shared.connection import AsyncConnectionManager, connection_manager


class ConsolidationEngine:
    def __init__(self, cm: AsyncConnectionManager = None):
        self._cm = cm or connection_manager

    async def consolidate_staging(self, user_id: str, staging_items: List[Dict[str, Any]],
                            min_importance: float = 0.7) -> Dict[str, int]:
        from core.memory import CoreMemory
        cm = CoreMemory(cm=self._cm)
        promoted = 0
        skipped = 0
        for item in staging_items:
            if item.get("importance", 0) < min_importance:
                skipped += 1
                continue
            content = item.get("content", "")
            key = "staging_%s" % content[:30].replace(" ", "_").lower()
            await cm.save(user_id, key, content, item.get("importance", 0.7))
            promoted += 1
        return {"promoted": promoted, "skipped": skipped}

    async def consolidate_episodes(self, user_id: str, episodic_db: str = None,
                             min_weight: float = 0.7) -> int:
        from core.memory import CoreMemory
        cm = CoreMemory(cm=self._cm)
        epi_db = episodic_db or "memory.db"
        epi_conn = await self._cm.get(epi_db)
        cursor = await epi_conn.execute(
            "SELECT summary, emotional_weight FROM episodes WHERE user_id=? AND emotional_weight > ? ORDER BY created_at DESC LIMIT 10",
            (user_id, min_weight)
        )
        rows = await cursor.fetchall()

        if not rows:
            return 0

        consolidated = 0
        for row in rows:
            summary = row["summary"]
            weight = row["emotional_weight"]
            key = "ep_%s" % summary[:30].replace(" ", "_").lower()
            await cm.save(user_id, key, summary[:200], weight)
            consolidated += 1
        return consolidated

    async def get_stats(self, user_id: str) -> Dict[str, int]:
        conn = await self._cm.get("memory.db")
        total_cursor = await conn.execute("SELECT COUNT(*) FROM core_memory WHERE user_id=?", (user_id,))
        total = (await total_cursor.fetchone())[0]
        high_cursor = await conn.execute("SELECT COUNT(*) FROM core_memory WHERE user_id=? AND importance > 0.7", (user_id,))
        high = (await high_cursor.fetchone())[0]
        low_cursor = await conn.execute("SELECT COUNT(*) FROM core_memory WHERE user_id=? AND importance < 0.3", (user_id,))
        low = (await low_cursor.fetchone())[0]
        return {"total": total, "high_importance": high, "low_importance": low}
