"""
Forgetting System - decay, archiving, compression
"""
import time
import json
import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any
from config import config

logger = logging.getLogger(__name__)

ARCHIVE_DIR = Path.home() / ".mcp-ariel-memory" / "archives"


class ForgettingSystem:
    def __init__(self, db_path: str = None, layer: str = "user"):
        self.db_path = db_path or str(Path.home() / ".mcp-ariel-memory" / "core_memory.db")
        self.layer = layer
        self.decay_rate = config.get_forgetting("decay_rate") or 0.01
        self.archive_days = config.get_forgetting("archive_threshold_days") or 90
        self.archive_min_importance = config.get_forgetting("archive_min_importance") or 0.3
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def decay_importance(self) -> int:
        conn = self._get_conn()
        try:
            now = time.time()
            cursor = conn.execute(
                """UPDATE core_memory SET importance = MAX(0.01,
                   importance * EXP(-? * (? - updated_at) / 86400))
                   WHERE importance > 0.01""",
                (self.decay_rate, now)
            )
            conn.commit()
            affected = cursor.rowcount
            if affected > 0:
                logger.info("Decayed %d entries" % affected)
            return affected
        except Exception as e:
            logger.error("Decay failed: %s" % e)
            return 0
        finally:
            conn.close()

    def archive_old_entries(self) -> int:
        conn = self._get_conn()
        try:
            cutoff = time.time() - (self.archive_days * 86400)
            rows = conn.execute(
                "SELECT * FROM core_memory WHERE updated_at < ? AND importance < ?",
                (cutoff, self.archive_min_importance)
            ).fetchall()
            if not rows:
                return 0

            archive_file = ARCHIVE_DIR / f"archive_{time.strftime('%Y%m%d')}.json"
            archive_data = []
            for row in rows:
                archive_data.append({
                    "user_id": row["user_id"], "key": row["key"],
                    "value": row["value"], "importance": row["importance"],
                    "updated_at": row["updated_at"],
                })

            existing = []
            if archive_file.exists():
                try:
                    existing = json.loads(archive_file.read_text(encoding="utf-8"))
                except Exception:
                    pass
            existing.extend(archive_data)
            archive_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

            ids = [row["entry_id"] for row in rows]
            placeholders = ",".join(["?"] * len(ids))
            conn.execute("DELETE FROM core_memory WHERE entry_id IN (%s)" % placeholders, ids)
            conn.commit()
            logger.info("Archived %d entries" % len(rows))
            return len(rows)
        except Exception as e:
            logger.error("Archive failed: %s" % e)
            return 0
        finally:
            conn.close()

    def compress_duplicates(self) -> int:
        conn = self._get_conn()
        try:
            duplicates = conn.execute(
                "SELECT user_id, key, COUNT(*) as cnt FROM core_memory GROUP BY user_id, key HAVING cnt > 1"
            ).fetchall()
            removed = 0
            for dup in duplicates:
                conn.execute(
                    """DELETE FROM core_memory WHERE user_id=? AND key=? AND entry_id NOT IN
                       (SELECT entry_id FROM core_memory WHERE user_id=? AND key=? ORDER BY updated_at DESC LIMIT 1)""",
                    (dup["user_id"], dup["key"], dup["user_id"], dup["key"])
                )
                removed += conn.execute("SELECT changes()").fetchone()[0]
            conn.commit()
            return removed
        except Exception as e:
            logger.error("Compression failed: %s" % e)
            return 0
        finally:
            conn.close()

    def cleanup(self) -> Dict[str, int]:
        return {
            "decayed": self.decay_importance(),
            "archived": self.archive_old_entries(),
            "compressed": self.compress_duplicates(),
        }
