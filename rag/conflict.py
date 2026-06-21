"""
Conflict Resolver - detects and resolves memory conflicts
"""
import uuid
import sqlite3
from typing import Dict, Any, List, Optional
from pathlib import Path


class ConflictResolver:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(Path.home() / ".mcp-ariel-memory" / "rag.db")
        self._init_conflicts_table()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_conflicts_table(self):
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS memory_conflicts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    is_conflict INTEGER DEFAULT 0,
                    conflict_group_id TEXT,
                    created_at REAL DEFAULT (strftime('%s','now'))
                );
                CREATE INDEX IF NOT EXISTS idx_conflicts_user ON memory_conflicts(user_id);
                CREATE INDEX IF NOT EXISTS idx_conflicts_group ON memory_conflicts(conflict_group_id);
            """)
            conn.commit()
        finally:
            conn.close()

    def check(self, user_id: str, new_content: str, min_similarity: float = 0.3) -> Dict[str, Any]:
        conn = self._get_conn()
        try:
            keywords = [w for w in new_content.split() if len(w) > 3][:5]
            if not keywords:
                return {"content": new_content, "is_conflict": False}

            like_conditions = " OR ".join(["content LIKE ?" for _ in keywords])
            like_params = [f"%{kw}%" for kw in keywords]
            rows = conn.execute(
                "SELECT id, content, is_conflict, conflict_group_id FROM memory_conflicts WHERE user_id=? AND (%s) LIMIT 5" % like_conditions,
                (user_id, *like_params)
            ).fetchall()

            for row in rows:
                existing_id, existing_content, is_conflict, group_id = row
                similarity = self._calculate_similarity(new_content, existing_content)
                if similarity > min_similarity and existing_content != new_content:
                    gid = group_id or str(uuid.uuid4())
                    if not is_conflict:
                        conn.execute("UPDATE memory_conflicts SET is_conflict=1, conflict_group_id=? WHERE id=?", (gid, existing_id))
                    conn.commit()
                    return {
                        "content": new_content, "is_conflict": True,
                        "conflict_group_id": gid, "conflicts_with_id": existing_id,
                        "similarity": similarity
                    }

            conn.execute(
                "INSERT INTO memory_conflicts (user_id, content) VALUES (?, ?)",
                (user_id, new_content)
            )
            conn.commit()
            return {"content": new_content, "is_conflict": False}
        finally:
            conn.close()

    def get_conflicts(self, conflict_group_id: str) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT id, content, created_at FROM memory_conflicts WHERE conflict_group_id=? ORDER BY created_at DESC",
                (conflict_group_id,)
            ).fetchall()
            return [{"id": r[0], "content": r[1], "created_at": r[2]} for r in rows]
        finally:
            conn.close()

    def resolve(self, conflict_group_id: str, keep_id: int) -> bool:
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM memory_conflicts WHERE conflict_group_id=? AND id!=?", (conflict_group_id, keep_id))
            conn.execute("UPDATE memory_conflicts SET is_conflict=0, conflict_group_id=NULL WHERE id=?", (keep_id,))
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union) if union else 0.0
