"""
L3 EpisodicMemory — async important moments with emotional weight
"""
import json
import time
from typing import List, Optional
from dataclasses import dataclass

from shared.connection import AsyncConnectionManager, connection_manager


@dataclass
class Episode:
    episode_id: int
    user_id: str
    summary: str
    emotional_weight: float
    tags: List[str]
    created_at: float


class EpisodicMemory:
    def __init__(self, cm: Optional[AsyncConnectionManager] = None):
        self._cm = cm or connection_manager

    async def _init_db(self):
        await self._cm.execute_script("memory.db", """
            CREATE TABLE IF NOT EXISTS episodes (
                episode_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                summary TEXT NOT NULL,
                emotional_weight REAL DEFAULT 0.5,
                tags TEXT,
                created_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_episodes_user ON episodes(user_id);
            CREATE INDEX IF NOT EXISTS idx_episodes_time ON episodes(created_at);
        """)

    async def save(self, user_id: str, summary: str, emotional_weight: float = 0.5, tags: List[str] = None) -> int:
        conn = await self._cm.get("memory.db")
        cursor = await conn.execute(
            "INSERT INTO episodes (user_id, summary, emotional_weight, tags, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, summary, emotional_weight, json.dumps(tags or []), time.time()),
        )
        await conn.commit()
        return cursor.lastrowid

    async def get_episodes(self, user_id: str, limit: int = 20, offset: int = 0) -> List[Episode]:
        conn = await self._cm.get("memory.db")
        cursor = await conn.execute(
            "SELECT * FROM episodes WHERE user_id=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (user_id, limit, offset),
        )
        rows = await cursor.fetchall()
        return [self._row_to_episode(r) for r in rows]

    async def search_by_tag(self, user_id: str, tag: str, limit: int = 10) -> List[Episode]:
        conn = await self._cm.get("memory.db")
        cursor = await conn.execute(
            "SELECT * FROM episodes WHERE user_id=? AND tags LIKE ? ORDER BY created_at DESC LIMIT ?",
            (user_id, f'%"{tag}"%', limit),
        )
        rows = await cursor.fetchall()
        return [self._row_to_episode(r) for r in rows]

    async def search(self, user_id: str, query: str, limit: int = 10) -> List:
        conn = await self._cm.get("memory.db")
        cursor = await conn.execute(
            "SELECT * FROM episodes WHERE user_id=? AND summary LIKE ? ORDER BY created_at DESC LIMIT ?",
            (user_id, f"%{query}%", limit),
        )
        rows = await cursor.fetchall()
        return [self._row_to_episode(r) for r in rows]

    async def archive_old(self, user_id: str, days: int = 90) -> int:
        conn = await self._cm.get("memory.db")
        cutoff = time.time() - (days * 86400)
        cursor = await conn.execute(
            "DELETE FROM episodes WHERE user_id=? AND created_at < ? AND emotional_weight < 0.3",
            (user_id, cutoff),
        )
        await conn.commit()
        return cursor.rowcount

    def _row_to_episode(self, row) -> Episode:
        return Episode(
            episode_id=row["episode_id"],
            user_id=row["user_id"],
            summary=row["summary"],
            emotional_weight=row["emotional_weight"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            created_at=row["created_at"],
        )
