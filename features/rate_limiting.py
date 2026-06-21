"""
Rate Limiter — SQLite-based per-user rate limiting (persistent across restarts).
Включает HTTP request rate limiting + WebSocket/SSE connection limiting.
"""
import sqlite3
import time
import threading
from pathlib import Path
from typing import Dict, Any, Set
from config import config


class RateLimiter:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(Path.home() / ".mcp-ariel-memory" / "rate_limit.db")
        self._max_per_user = config.get("security", "rate_limit_per_user") or 100
        self._window_seconds = 60
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
                CREATE TABLE IF NOT EXISTS rate_limits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    timestamp REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_rl_user ON rate_limits(user_id);
                CREATE INDEX IF NOT EXISTS idx_rl_time ON rate_limits(timestamp);
            """)
            conn.commit()
        finally:
            conn.close()

    def check(self, user_id: str) -> Dict[str, Any]:
        now = time.time()
        cutoff = now - self._window_seconds

        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM rate_limits WHERE timestamp < ?", (cutoff,))
            conn.execute("INSERT INTO rate_limits (user_id, timestamp) VALUES (?, ?)", (user_id, now))

            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM rate_limits WHERE user_id=? AND timestamp >= ?",
                (user_id, cutoff)
            ).fetchone()
            count = row["cnt"] if row else 0

            conn.commit()

            if count > self._max_per_user:
                oldest = conn.execute(
                    "SELECT MIN(timestamp) as ts FROM rate_limits WHERE user_id=? AND timestamp >= ?",
                    (user_id, cutoff)
                ).fetchone()
                reset_in = int(self._window_seconds - (now - (oldest["ts"] if oldest else now)))
                return {"allowed": False, "remaining": 0, "reset_in": max(reset_in, 1)}

            return {"allowed": True, "remaining": self._max_per_user - count}
        finally:
            conn.close()

    def get_stats(self, user_id: str) -> Dict[str, Any]:
        cutoff = time.time() - self._window_seconds
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM rate_limits WHERE user_id=? AND timestamp >= ?",
                (user_id, cutoff)
            ).fetchone()
            count = row["cnt"] if row else 0
            return {"requests_last_minute": count, "limit": self._max_per_user}
        finally:
            conn.close()

    def cleanup_old(self) -> int:
        cutoff = time.time() - (self._window_seconds * 10)
        conn = self._get_conn()
        try:
            cursor = conn.execute("DELETE FROM rate_limits WHERE timestamp < ?", (cutoff,))
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()


class ConnectionLimiter:
    """Лимит одновременных WebSocket/SSE соединений per user."""

    def __init__(self, max_connections_per_user: int = None, max_total: int = None):
        self._max_per_user = max_connections_per_user or config.get("security", "max_ws_per_user") or 5
        self._max_total = max_total or config.get("security", "max_ws_total") or 100
        self._connections: Dict[str, Set[str]] = {}  # user_id -> set of connection_ids
        self._total = 0
        self._lock = threading.Lock()

    def acquire(self, user_id: str, connection_id: str) -> Dict[str, Any]:
        """Попытаться занять соединение. Возвращает allowed/rejected."""
        with self._lock:
            user_conns = self._connections.setdefault(user_id, set())

            if len(user_conns) >= self._max_per_user:
                return {
                    "allowed": False,
                    "reason": "user_limit",
                    "current": len(user_conns),
                    "max": self._max_per_user,
                }

            if self._total >= self._max_total:
                return {
                    "allowed": False,
                    "reason": "total_limit",
                    "current": self._total,
                    "max": self._max_total,
                }

            user_conns.add(connection_id)
            self._total += 1

            return {
                "allowed": True,
                "user_connections": len(user_conns),
                "total_connections": self._total,
            }

    def release(self, user_id: str, connection_id: str):
        """Освободить соединение."""
        with self._lock:
            user_conns = self._connections.get(user_id, set())
            user_conns.discard(connection_id)
            self._total = max(0, self._total - 1)
            if not user_conns:
                self._connections.pop(user_id, None)

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_connections": self._total,
                "max_total": self._max_total,
                "max_per_user": self._max_per_user,
                "users": {uid: len(conns) for uid, conns in self._connections.items()},
            }

    def get_user_connections(self, user_id: str) -> int:
        with self._lock:
            return len(self._connections.get(user_id, set()))
