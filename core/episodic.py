"""
L3 EpisodicMemory - important moments with emotional weight
"""
import json
import time
import sqlite3
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class Episode:
    episode_id: int
    user_id: str
    summary: str
    emotional_weight: float
    tags: List[str]
    created_at: float

class EpisodicMemory:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(Path.home() / ".mcp-ariel-memory" / "episodic.db")
        self._init_db()
    
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn
    
    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_conn()
        try:
            conn.executescript("""
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
                CREATE INDEX IF NOT EXISTS idx_episodes_weight ON episodes(emotional_weight);
            """)
            conn.commit()
        finally:
            conn.close()
    
    def save(self, user_id: str, summary: str, emotional_weight: float = 0.5, tags: List[str] = None) -> int:
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "INSERT INTO episodes (user_id, summary, emotional_weight, tags, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, summary, emotional_weight, json.dumps(tags or []), time.time())
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()
    
    def get_episodes(self, user_id: str, limit: int = 20, offset: int = 0) -> List[Episode]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM episodes WHERE user_id=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (user_id, limit, offset)
            ).fetchall()
            return [self._row_to_episode(r) for r in rows]
        finally:
            conn.close()
    
    def search_by_tag(self, user_id: str, tag: str, limit: int = 10) -> List[Episode]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM episodes WHERE user_id=? AND tags LIKE ? ORDER BY created_at DESC LIMIT ?",
                (user_id, f'%"{tag}"%', limit)
            ).fetchall()
            return [self._row_to_episode(r) for r in rows]
        finally:
            conn.close()
    
    def search(self, user_id: str, query: str, limit: int = 10) -> List:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM episodes WHERE user_id=? AND summary LIKE ? ORDER BY created_at DESC LIMIT ?",
                (user_id, f"%{query}%", limit)
            ).fetchall()
            return [self._row_to_episode(r) for r in rows]
        finally:
            conn.close()

    def archive_old(self, user_id: str, days: int = 90) -> int:
        import time
        conn = self._get_conn()
        try:
            cutoff = time.time() - (days * 86400)
            cursor = conn.execute(
                "DELETE FROM episodes WHERE user_id=? AND created_at < ? AND emotional_weight < 0.3",
                (user_id, cutoff)
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    def _row_to_episode(self, row) -> Episode:
        return Episode(
            episode_id=row["episode_id"],
            user_id=row["user_id"],
            summary=row["summary"],
            emotional_weight=row["emotional_weight"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            created_at=row["created_at"]
        )
