"""
Consolidation Engine - L1→L2→L3→L4 memory promotion
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
        promoted = 0
        skipped = 0
        for item in staging_items:
            if item.get("importance", 0) < min_importance:
                skipped += 1
                continue
            content = item.get("content", "")
            key = f"staging_{content[:30].replace(' ', '_').lower()}"
            await self._save_to_core(user_id, key, content, item.get("importance", 0.7))
            promoted += 1
        return {"promoted": promoted, "skipped": skipped}

    async def consolidate_episodes(self, user_id: str, episodic_db: str = None,
                             min_weight: float = 0.7) -> int:
        epi_db = episodic_db or "episodic.db"
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
            key = f"ep_{summary[:30].replace(' ', '_').lower()}"
            await self._save_to_core(user_id, key, summary[:200], weight)
            consolidated += 1
        return consolidated

    async def _save_to_core(self, user_id: str, key: str, value: str, importance: float):
        conn = await self._cm.get("core_memory.db")
        now = time.time()
        cursor = await conn.execute(
            "SELECT entry_id FROM core_memory WHERE user_id=? AND key=?", (user_id, key)
        )
        existing = await cursor.fetchone()
        if existing:
            await conn.execute(
                "UPDATE core_memory SET value=?, importance=?, updated_at=? WHERE entry_id=?",
                (value, importance, now, existing["entry_id"])
            )
        else:
            await conn.execute(
                "INSERT INTO core_memory (user_id, key, value, importance, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, key, value, importance, now, now)
            )
        await conn.commit()

    async def get_stats(self, user_id: str) -> Dict[str, int]:
        conn = await self._cm.get("core_memory.db")
        total_cursor = await conn.execute("SELECT COUNT(*) FROM core_memory WHERE user_id=?", (user_id,))
        total = (await total_cursor.fetchone())[0]
        high_cursor = await conn.execute("SELECT COUNT(*) FROM core_memory WHERE user_id=? AND importance > 0.7", (user_id,))
        high = (await high_cursor.fetchone())[0]
        low_cursor = await conn.execute("SELECT COUNT(*) FROM core_memory WHERE user_id=? AND importance < 0.3", (user_id,))
        low = (await low_cursor.fetchone())[0]
        return {"total": total, "high_importance": high, "low_importance": low}
