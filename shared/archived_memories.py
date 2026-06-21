"""
Archived Memories — хранилище архивированных записей.
Из оригинала: agent_core/cognitive/forgetting_ritual.py
"""
import sqlite3
import time
from pathlib import Path
from typing import List, Dict, Any, Optional


class ArchivedMemories:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(Path.home() / ".mcp-ariel-memory" / "cognitive.db")
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS archived_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL DEFAULT 'default',
                    original_id INTEGER,
                    content TEXT NOT NULL,
                    memory_type TEXT,
                    importance REAL,
                    archive_reason TEXT NOT NULL,
                    archived_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_archived_user ON archived_memories(user_id);
                CREATE INDEX IF NOT EXISTS idx_archived_reason ON archived_memories(archive_reason);
            """)
            conn.commit()
        finally:
            conn.close()

    def archive(self, user_id: str, content: str, memory_type: str = None,
                importance: float = None, original_id: int = None, reason: str = "manual") -> int:
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "INSERT INTO archived_memories (user_id, original_id, content, memory_type, importance, archive_reason) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, original_id, content, memory_type, importance, reason)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_archived(self, user_id: str = "default", limit: int = 50) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT id, original_id, content, memory_type, importance, archive_reason, archived_at FROM archived_memories WHERE user_id=? ORDER BY archived_at DESC LIMIT ?",
                (user_id, limit)
            ).fetchall()
            return [{"id": r[0], "original_id": r[1], "content": r[2],
                     "memory_type": r[3], "importance": r[4],
                     "archive_reason": r[5], "archived_at": r[6]} for r in rows]
        finally:
            conn.close()

    def count(self, user_id: str = "default") -> int:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT COUNT(*) FROM archived_memories WHERE user_id=?", (user_id,)).fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    def restore(self, archived_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM archived_memories WHERE id=?", (archived_id,)).fetchone()
            if row:
                conn.execute("DELETE FROM archived_memories WHERE id=?", (archived_id,))
                conn.commit()
                return {"content": row["content"], "memory_type": row["memory_type"],
                        "importance": row["importance"]}
            return None
        finally:
            conn.close()


archived_memories = ArchivedMemories()
