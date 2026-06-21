"""
L2 SessionStore - session history with indexes
"""
import json
import time
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass, field

@dataclass
class SessionRecord:
    session_id: str
    user_id: str
    summary: str
    state_deltas: Dict = field(default_factory=dict)
    topics: List[str] = field(default_factory=list)
    message_count: int = 0
    started_at: float = 0.0
    ended_at: float = 0.0

class SessionStore:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(Path.home() / ".mcp-ariel-memory" / "sessions.db")
        self._init_db()
    
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn
    
    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    summary TEXT,
                    state_deltas TEXT,
                    topics TEXT,
                    message_count INTEGER DEFAULT 0,
                    started_at REAL NOT NULL,
                    ended_at REAL
                );
                CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
                CREATE INDEX IF NOT EXISTS idx_sessions_time ON sessions(started_at);
                CREATE INDEX IF NOT EXISTS idx_sessions_user_time ON sessions(user_id, started_at);
            """)
            conn.commit()
        finally:
            conn.close()
    
    def create_session(self, user_id: str) -> str:
        import uuid
        session_id = f"sess_{user_id}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO sessions (session_id, user_id, started_at) VALUES (?, ?, ?)",
                (session_id, user_id, time.time())
            )
            conn.commit()
        finally:
            conn.close()
        return session_id
    
    def close_session(self, session_id: str, summary: str = "", state_deltas: Dict = None, topics: List[str] = None):
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE sessions SET summary=?, state_deltas=?, topics=?, ended_at=? WHERE session_id=?",
                (summary, json.dumps(state_deltas or {}), json.dumps(topics or []), time.time(), session_id)
            )
            conn.commit()
        finally:
            conn.close()
    
    def get_recent_sessions(self, user_id: str, limit: int = 10) -> List[SessionRecord]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM sessions WHERE user_id=? ORDER BY started_at DESC LIMIT ?",
                (user_id, limit)
            ).fetchall()
            return [self._row_to_record(r) for r in rows]
        finally:
            conn.close()
    
    def get_session_summary(self, user_id: str) -> str:
        sessions = self.get_recent_sessions(user_id, 3)
        if not sessions:
            return "No sessions yet."
        return "\n".join([f"- {s.summary[:80]}" for s in sessions if s.summary])
    
    def count_sessions(self, user_id: str = None) -> int:
        conn = self._get_conn()
        try:
            if user_id:
                row = conn.execute("SELECT COUNT(*) FROM sessions WHERE user_id=?", (user_id,)).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()
            return row[0] if row else 0
        finally:
            conn.close()
    
    def _row_to_record(self, row) -> SessionRecord:
        return SessionRecord(
            session_id=row["session_id"],
            user_id=row["user_id"],
            summary=row["summary"] or "",
            state_deltas=json.loads(row["state_deltas"]) if row["state_deltas"] else {},
            topics=json.loads(row["topics"]) if row["topics"] else [],
            message_count=row["message_count"],
            started_at=row["started_at"],
            ended_at=row["ended_at"]
        )
