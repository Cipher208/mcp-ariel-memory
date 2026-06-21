"""
Memory Compressor - compress and deduplicate memory
"""
import sqlite3
from pathlib import Path
from typing import Dict, Any


class MemoryCompressor:
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or str(Path.home() / ".mcp-ariel-memory"))

    def deduplicate_core(self, user_id: str) -> int:
        db = str(self.base_dir / "core_memory.db")
        conn = sqlite3.connect(db)
        try:
            duplicates = conn.execute(
                "SELECT user_id, key, COUNT(*) as cnt FROM core_memory WHERE user_id=? GROUP BY user_id, key HAVING cnt > 1",
                (user_id,)
            ).fetchall()
            removed = 0
            for dup in duplicates:
                conn.execute(
                    """DELETE FROM core_memory WHERE user_id=? AND key=? AND entry_id NOT IN
                       (SELECT entry_id FROM core_memory WHERE user_id=? AND key=? ORDER BY updated_at DESC LIMIT 1)""",
                    (dup[0], dup[1], dup[0], dup[1])
                )
                removed += conn.execute("SELECT changes()").fetchone()[0]
            conn.commit()
            return removed
        finally:
            conn.close()

    def compress_episodes(self, user_id: str, min_weight: float = 0.3) -> int:
        db = str(self.base_dir / "episodic.db")
        conn = sqlite3.connect(db)
        try:
            cursor = conn.execute(
                "DELETE FROM episodes WHERE user_id=? AND emotional_weight < ? AND created_at < ?",
                (user_id, min_weight, __import__("time").time() - 30 * 86400)
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    def get_stats(self, user_id: str) -> Dict[str, int]:
        stats = {}
        for name, db_file in [("core", "core_memory.db"), ("episodes", "episodic.db"), ("sessions", "sessions.db")]:
            db = str(self.base_dir / db_file)
            conn = sqlite3.connect(db)
            try:
                tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
                total = 0
                for table in tables:
                    try:
                        row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                        total += row[0] if row else 0
                    except Exception:
                        pass
                stats[name] = total
            finally:
                conn.close()
        return stats
