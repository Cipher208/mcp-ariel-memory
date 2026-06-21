"""
Audit Trail - log all memory changes
"""
import sqlite3
import time
import json
from pathlib import Path
from typing import List, Dict, Any
from config import config


class AuditTrail:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(Path.home() / ".mcp-ariel-memory" / "audit.db")
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    layer TEXT,
                    target_id TEXT,
                    details TEXT,
                    timestamp REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id);
                CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(timestamp);
                CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);
            """)
            conn.commit()
        finally:
            conn.close()

    def log(self, user_id: str, action: str, layer: str = None,
            target_id: str = None, details: Dict = None):
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO audit_log (user_id, action, layer, target_id, details, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, action, layer, target_id, json.dumps(details or {}), time.time())
            )
            conn.commit()
        finally:
            conn.close()

    def get_history(self, user_id: str, limit: int = 50, action: str = None) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            if action:
                rows = conn.execute(
                    "SELECT * FROM audit_log WHERE user_id=? AND action=? ORDER BY timestamp DESC LIMIT ?",
                    (user_id, action, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM audit_log WHERE user_id=? ORDER BY timestamp DESC LIMIT ?",
                    (user_id, limit)
                ).fetchall()
            return [
                {"log_id": r["log_id"], "action": r["action"], "layer": r["layer"],
                 "target_id": r["target_id"], "details": json.loads(r["details"]) if r["details"] else {},
                 "timestamp": r["timestamp"]}
                for r in rows
            ]
        finally:
            conn.close()

    def count(self, user_id: str = None) -> int:
        conn = self._get_conn()
        try:
            if user_id:
                row = conn.execute("SELECT COUNT(*) FROM audit_log WHERE user_id=?", (user_id,)).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    def cleanup_old(self, retention_days: int = 30) -> int:
        """Удалить записи старше retention_days."""
        cutoff = time.time() - (retention_days * 86400)
        conn = self._get_conn()
        try:
            cursor = conn.execute("DELETE FROM audit_log WHERE timestamp < ?", (cutoff,))
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    def archive_and_prune(self, retention_days: int = 30, archive_dir: str = None) -> Dict[str, int]:
        """Архивировать старые записи в JSON, затем удалить."""
        import json
        from pathlib import Path

        cutoff = time.time() - (retention_days * 86400)
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM audit_log WHERE timestamp < ? ORDER BY timestamp",
                (cutoff,)
            ).fetchall()

            if not rows:
                return {"archived": 0, "pruned": 0}

            # Архивировать
            if archive_dir:
                archive_path = Path(archive_dir)
                archive_path.mkdir(parents=True, exist_ok=True)
                archive_file = archive_path / "audit_archive_%d.json" % int(time.time())
                archive_data = [
                    {"log_id": r["log_id"], "user_id": r["user_id"], "action": r["action"],
                     "layer": r["layer"], "target_id": r["target_id"],
                     "details": json.loads(r["details"]) if r["details"] else {},
                     "timestamp": r["timestamp"]}
                    for r in rows
                ]
                archive_file.write_text(json.dumps(archive_data, indent=2, default=str), encoding="utf-8")

            # Удалить
            cursor = conn.execute("DELETE FROM audit_log WHERE timestamp < ?", (cutoff,))
            conn.commit()
            return {"archived": len(rows), "pruned": cursor.rowcount}
        finally:
            conn.close()

    def count_all(self) -> int:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()
            return row[0] if row else 0
        finally:
            conn.close()
