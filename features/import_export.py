"""
Import/Export - export and import memory between instances
"""
import json
import sqlite3
import time
from pathlib import Path
from typing import Dict, Any, List
from config import config


class ImportExport:
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or str(Path.home() / ".mcp-ariel-memory"))
        self.export_dir = self.base_dir / "exports"
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export_user(self, user_id: str, db_path: str = None) -> str:
        db = db_path or str(self.base_dir / "core_memory.db")
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        try:
            data = {
                "user_id": user_id,
                "exported_at": time.time(),
                "version": "1.0",
                "core_memory": [],
                "episodes": [],
                "sessions": [],
            }

            rows = conn.execute("SELECT * FROM core_memory WHERE user_id=?", (user_id,)).fetchall()
            for r in rows:
                data["core_memory"].append({
                    "key": r["key"], "value": r["value"],
                    "importance": r["importance"], "created_at": r["created_at"],
                })

            epi_db = str(self.base_dir / "episodic.db")
            epi_conn = sqlite3.connect(epi_db)
            epi_conn.row_factory = sqlite3.Row
            rows = epi_conn.execute("SELECT * FROM episodes WHERE user_id=?", (user_id,)).fetchall()
            for r in rows:
                data["episodes"].append({
                    "summary": r["summary"], "emotional_weight": r["emotional_weight"],
                    "tags": r["tags"], "created_at": r["created_at"],
                })
            epi_conn.close()

            sess_db = str(self.base_dir / "sessions.db")
            sess_conn = sqlite3.connect(sess_db)
            sess_conn.row_factory = sqlite3.Row
            rows = sess_conn.execute("SELECT * FROM sessions WHERE user_id=?", (user_id,)).fetchall()
            for r in rows:
                data["sessions"].append({
                    "session_id": r["session_id"], "summary": r["summary"],
                    "started_at": r["started_at"], "ended_at": r["ended_at"],
                })
            sess_conn.close()

            filename = f"export_{user_id}_{int(time.time())}.json"
            filepath = self.export_dir / filename
            filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return str(filepath)
        finally:
            conn.close()

    def import_user(self, filepath: str, target_user_id: str = None) -> Dict[str, int]:
        data = json.loads(Path(filepath).read_text(encoding="utf-8"))
        user_id = target_user_id or data.get("user_id", "default")

        db = str(self.base_dir / "core_memory.db")
        conn = sqlite3.connect(db)
        imported = {"core_memory": 0, "episodes": 0, "sessions": 0}

        try:
            for item in data.get("core_memory", []):
                conn.execute(
                    "INSERT OR REPLACE INTO core_memory (user_id, key, value, importance, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, item["key"], item["value"], item["importance"], item["created_at"], time.time())
                )
                imported["core_memory"] += 1
            conn.commit()
        finally:
            conn.close()

        for item in data.get("episodes", []):
            epi_db = str(self.base_dir / "episodic.db")
            epi_conn = sqlite3.connect(epi_db)
            epi_conn.execute(
                "INSERT INTO episodes (user_id, summary, emotional_weight, tags, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, item["summary"], item["emotional_weight"], item["tags"], item["created_at"])
            )
            epi_conn.commit()
            epi_conn.close()
            imported["episodes"] += 1

        return imported

    def list_exports(self) -> List[Dict[str, Any]]:
        exports = []
        for f in sorted(self.export_dir.glob("export_*.json"), reverse=True):
            exports.append({"file": f.name, "size": f.stat().st_size})
        return exports
