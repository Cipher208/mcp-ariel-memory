"""
DB Pool - connection pool for SQLite
"""
import sqlite3
import threading
from pathlib import Path
from typing import Dict, Optional
from config import config


class DBPool:
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or str(Path.home() / ".mcp-ariel-memory"))
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._pool: Dict[str, sqlite3.Connection] = {}
        self._lock = threading.Lock()
        self._pool_size = config.get("performance", "connection_pool_size") or 10

    def get(self, db_name: str = "core_memory.db") -> sqlite3.Connection:
        with self._lock:
            if db_name in self._pool:
                return self._pool[db_name]

            db_path = str(self.base_dir / db_name)
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("PRAGMA synchronous=NORMAL")

            if len(self._pool) < self._pool_size:
                self._pool[db_name] = conn

            return conn

    def close_all(self):
        with self._lock:
            for conn in self._pool.values():
                try:
                    conn.close()
                except Exception:
                    pass
            self._pool.clear()

    def stats(self) -> Dict[str, int]:
        return {"pool_size": len(self._pool), "max_size": self._pool_size}
