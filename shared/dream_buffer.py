"""
Dream Buffer (staging_memories) — промежуточное хранилище перед консолидацией.
Из оригинала: agent_core/cognitive/dream_buffer.py
"""
import json
import sqlite3
import time
from pathlib import Path
from typing import List, Dict, Any, Optional


class DreamBuffer:
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
                CREATE TABLE IF NOT EXISTS staging_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL DEFAULT 'default',
                    session_id TEXT NOT NULL,
                    event_id TEXT,
                    content TEXT NOT NULL,
                    importance REAL DEFAULT 0.5,
                    metadata TEXT DEFAULT '{}',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_staging_user ON staging_memories(user_id);
                CREATE INDEX IF NOT EXISTS idx_staging_session ON staging_memories(session_id);
            """)
            conn.commit()
        finally:
            conn.close()

    def add(self, user_id: str, session_id: str, content: str,
            importance: float = 0.5, event_id: str = None, metadata: Dict = None) -> int:
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "INSERT INTO staging_memories (user_id, session_id, event_id, content, importance, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, session_id, event_id, content, importance, json.dumps(metadata or {}))
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_staging(self, user_id: str = "default", session_id: str = None) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            if session_id:
                rows = conn.execute(
                    "SELECT id, content, importance, metadata, created_at FROM staging_memories WHERE user_id=? AND session_id=? ORDER BY created_at",
                    (user_id, session_id)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, content, importance, metadata, created_at FROM staging_memories WHERE user_id=? ORDER BY created_at",
                    (user_id,)
                ).fetchall()
            return [{"id": r[0], "content": r[1], "importance": r[2],
                     "metadata": json.loads(r[3]) if r[3] else {}, "created_at": r[4]} for r in rows]
        finally:
            conn.close()

    def clear_staging(self, user_id: str = "default", session_id: str = None) -> int:
        conn = self._get_conn()
        try:
            if session_id:
                cursor = conn.execute("DELETE FROM staging_memories WHERE user_id=? AND session_id=?", (user_id, session_id))
            else:
                cursor = conn.execute("DELETE FROM staging_memories WHERE user_id=?", (user_id,))
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    def cleanup_old(self, max_age_hours: int = 24, max_count: int = 500) -> Dict[str, int]:
        """Очистка по возрасту и количеству."""
        import time
        now = time.time()
        conn = self._get_conn()
        result = {"by_age": 0, "by_count": 0}
        try:
            # Удалить по возрасту
            cutoff = now - (max_age_hours * 3600)
            cursor = conn.execute(
                "DELETE FROM staging_memories WHERE created_at < datetime(?, 'unixepoch')",
                (cutoff,)
            )
            result["by_age"] = cursor.rowcount

            # Удалить лишние по количеству (оставить max_count самых свежих)
            rows = conn.execute(
                "SELECT user_id, COUNT(*) as cnt FROM staging_memories GROUP BY user_id HAVING cnt > ?",
                (max_count,)
            ).fetchall()
            for row in rows:
                uid = row[0]
                excess = row[1] - max_count
                cursor = conn.execute(
                    """DELETE FROM staging_memories WHERE id IN (
                        SELECT id FROM staging_memories WHERE user_id=?
                        ORDER BY created_at ASC LIMIT ?
                    )""",
                    (uid, excess)
                )
                result["by_count"] += cursor.rowcount

            conn.commit()
            return result
        finally:
            conn.close()

    def count_all(self) -> int:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT COUNT(*) FROM staging_memories").fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    def count(self, user_id: str = "default", session_id: str = None) -> int:
        conn = self._get_conn()
        try:
            if session_id:
                row = conn.execute("SELECT COUNT(*) FROM staging_memories WHERE user_id=? AND session_id=?", (user_id, session_id)).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) FROM staging_memories WHERE user_id=?", (user_id,)).fetchone()
            return row[0] if row else 0
        finally:
            conn.close()


dream_buffer = DreamBuffer()
