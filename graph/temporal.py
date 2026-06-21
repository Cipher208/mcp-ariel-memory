"""
Temporal Graph - time-based memory relations
"""
import sqlite3
import time
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class TemporalEvent:
    event_id: int
    user_id: str
    event_type: str
    content: str
    timestamp: float
    importance: float
    metadata: Dict


class TemporalGraph:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(Path.home() / ".mcp-ariel-memory" / "graph.db")
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
                CREATE TABLE IF NOT EXISTS temporal_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    importance REAL DEFAULT 0.5,
                    metadata TEXT
                );
                CREATE TABLE IF NOT EXISTS temporal_links (
                    from_event INTEGER NOT NULL,
                    to_event INTEGER NOT NULL,
                    link_type TEXT NOT NULL DEFAULT 'follows',
                    strength REAL DEFAULT 0.5,
                    PRIMARY KEY (from_event, to_event, link_type)
                );
                CREATE INDEX IF NOT EXISTS idx_temp_user ON temporal_events(user_id);
                CREATE INDEX IF NOT EXISTS idx_temp_time ON temporal_events(timestamp);
                CREATE INDEX IF NOT EXISTS idx_temp_type ON temporal_events(event_type);
            """)
            conn.commit()
        finally:
            conn.close()

    def add_event(self, user_id: str, event_type: str, content: str,
                  importance: float = 0.5, metadata: Dict = None) -> int:
        conn = self._get_conn()
        try:
            import json
            cursor = conn.execute(
                "INSERT INTO temporal_events (user_id, event_type, content, timestamp, importance, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, event_type, content, time.time(), importance, json.dumps(metadata or {}))
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def link_events(self, from_event: int, to_event: int, link_type: str = "follows", strength: float = 0.5):
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO temporal_links (from_event, to_event, link_type, strength) VALUES (?, ?, ?, ?)",
                (from_event, to_event, link_type, strength)
            )
            conn.commit()
        finally:
            conn.close()

    def get_timeline(self, user_id: str, limit: int = 50, offset: int = 0) -> List[TemporalEvent]:
        conn = self._get_conn()
        try:
            import json
            rows = conn.execute(
                "SELECT * FROM temporal_events WHERE user_id=? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                (user_id, limit, offset)
            ).fetchall()
            return [
                TemporalEvent(
                    event_id=r["event_id"], user_id=r["user_id"], event_type=r["event_type"],
                    content=r["content"], timestamp=r["timestamp"], importance=r["importance"],
                    metadata=json.loads(r["metadata"]) if r["metadata"] else {}
                ) for r in rows
            ]
        finally:
            conn.close()

    def get_events_near(self, user_id: str, timestamp: float, window_seconds: float = 3600,
                        limit: int = 20) -> List[TemporalEvent]:
        conn = self._get_conn()
        try:
            import json
            rows = conn.execute(
                "SELECT * FROM temporal_events WHERE user_id=? AND ABS(timestamp - ?) < ? ORDER BY timestamp LIMIT ?",
                (user_id, timestamp, window_seconds, limit)
            ).fetchall()
            return [
                TemporalEvent(
                    event_id=r["event_id"], user_id=r["user_id"], event_type=r["event_type"],
                    content=r["content"], timestamp=r["timestamp"], importance=r["importance"],
                    metadata=json.loads(r["metadata"]) if r["metadata"] else {}
                ) for r in rows
            ]
        finally:
            conn.close()

    def get_causal_chain(self, event_id: int, direction: str = "forward", limit: int = 10) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            if direction == "forward":
                sql = "SELECT tl.to_event, te.event_type, te.content, te.timestamp FROM temporal_links tl JOIN temporal_events te ON tl.to_event = te.event_id WHERE tl.from_event = ? LIMIT ?"
            else:
                sql = "SELECT tl.from_event, te.event_type, te.content, te.timestamp FROM temporal_links tl JOIN temporal_events te ON tl.from_event = te.event_id WHERE tl.to_event = ? LIMIT ?"
            rows = conn.execute(sql, (event_id, limit)).fetchall()
            return [{"event_id": r[0], "type": r[1], "content": r[2], "timestamp": r[3]} for r in rows]
        finally:
            conn.close()

    def count_events(self, user_id: str = None) -> int:
        conn = self._get_conn()
        try:
            if user_id:
                row = conn.execute("SELECT COUNT(*) FROM temporal_events WHERE user_id=?", (user_id,)).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) FROM temporal_events").fetchone()
            return row[0] if row else 0
        finally:
            conn.close()
