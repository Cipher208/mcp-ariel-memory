"""
L4 CoreMemory - key-value facts with importance
"""
import time
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass

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
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(Path.home() / ".mcp-ariel-memory" / "core_memory.db")
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
                CREATE TABLE IF NOT EXISTS core_memory (
                    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    importance REAL DEFAULT 0.5,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_core_user ON core_memory(user_id);
                CREATE INDEX IF NOT EXISTS idx_core_key ON core_memory(key);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_core_user_key ON core_memory(user_id, key);
            """)
            conn.commit()
        finally:
            conn.close()
    
    def save(self, user_id: str, key: str, value: str, importance: float = 0.5) -> int:
        now = time.time()
        conn = self._get_conn()
        try:
            existing = conn.execute(
                "SELECT entry_id FROM core_memory WHERE user_id=? AND key=?", (user_id, key)
            ).fetchone()
            
            if existing:
                conn.execute(
                    "UPDATE core_memory SET value=?, importance=?, updated_at=? WHERE entry_id=?",
                    (value, importance, now, existing["entry_id"])
                )
                entry_id = existing["entry_id"]
            else:
                cursor = conn.execute(
                    "INSERT INTO core_memory (user_id, key, value, importance, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, key, value, importance, now, now)
                )
                entry_id = cursor.lastrowid
            
            conn.commit()
            return entry_id
        finally:
            conn.close()
    
    def get(self, user_id: str, key: str) -> Optional[CoreEntry]:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM core_memory WHERE user_id=? AND key=?", (user_id, key)
            ).fetchone()
            return self._row_to_entry(row) if row else None
        finally:
            conn.close()
    
    def get_all(self, user_id: str, limit: int = 50) -> List[CoreEntry]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM core_memory WHERE user_id=? ORDER BY importance DESC LIMIT ?",
                (user_id, limit)
            ).fetchall()
            return [self._row_to_entry(r) for r in rows]
        finally:
            conn.close()
    
    def delete(self, user_id: str, key: str) -> bool:
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "DELETE FROM core_memory WHERE user_id=? AND key=?", (user_id, key)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def search(self, user_id: str, query: str, limit: int = 10) -> List[Dict]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM core_memory WHERE user_id=? AND (key LIKE ? OR value LIKE ?) ORDER BY importance DESC LIMIT ?",
                (user_id, f"%{query}%", f"%{query}%", limit)
            ).fetchall()
            return [{"key": r["key"], "value": r["value"], "importance": r["importance"]} for r in rows]
        finally:
            conn.close()

    def count(self, user_id: str = None) -> int:
        conn = self._get_conn()
        try:
            if user_id:
                row = conn.execute("SELECT COUNT(*) FROM core_memory WHERE user_id=?", (user_id,)).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) FROM core_memory").fetchone()
            return row[0] if row else 0
        finally:
            conn.close()
    
    def _row_to_entry(self, row) -> CoreEntry:
        return CoreEntry(
            entry_id=row["entry_id"],
            user_id=row["user_id"],
            key=row["key"],
            value=row["value"],
            importance=row["importance"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )
