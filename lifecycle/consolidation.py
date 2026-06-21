"""
Consolidation Engine - L1→L2→L3→L4 memory promotion
"""
import time
import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List


class ConsolidationEngine:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(Path.home() / ".mcp-ariel-memory" / "core_memory.db")

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def consolidate_staging(self, user_id: str, staging_items: List[Dict[str, Any]],
                            min_importance: float = 0.7) -> Dict[str, int]:
        promoted = 0
        skipped = 0
        for item in staging_items:
            if item.get("importance", 0) < min_importance:
                skipped += 1
                continue
            content = item.get("content", "")
            key = f"staging_{content[:30].replace(' ', '_').lower()}"
            self._save_to_core(user_id, key, content, item.get("importance", 0.7))
            promoted += 1
        return {"promoted": promoted, "skipped": skipped}

    def consolidate_episodes(self, user_id: str, episodic_db: str = None,
                             min_weight: float = 0.7) -> int:
        epi_db = episodic_db or str(Path.home() / ".mcp-ariel-memory" / "episodic.db")
        epi_conn = sqlite3.connect(epi_db)
        epi_conn.row_factory = sqlite3.Row
        try:
            rows = epi_conn.execute(
                "SELECT summary, emotional_weight FROM episodes WHERE user_id=? AND emotional_weight > ? ORDER BY created_at DESC LIMIT 10",
                (user_id, min_weight)
            ).fetchall()
        finally:
            epi_conn.close()

        if not rows:
            return 0

        consolidated = 0
        for row in rows:
            summary = row["summary"]
            weight = row["emotional_weight"]
            key = f"ep_{summary[:30].replace(' ', '_').lower()}"
            self._save_to_core(user_id, key, summary[:200], weight)
            consolidated += 1
        return consolidated

    def _save_to_core(self, user_id: str, key: str, value: str, importance: float):
        conn = self._get_conn()
        try:
            now = time.time()
            existing = conn.execute(
                "SELECT entry_id FROM core_memory WHERE user_id=? AND key=?", (user_id, key)
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE core_memory SET value=?, importance=?, updated_at=? WHERE entry_id=?",
                    (value, importance, now, existing["entry_id"])
                )
            else:
                conn.execute(
                    "INSERT INTO core_memory (user_id, key, value, importance, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, key, value, importance, now, now)
                )
            conn.commit()
        finally:
            conn.close()

    def get_stats(self, user_id: str) -> Dict[str, int]:
        conn = self._get_conn()
        try:
            total = conn.execute("SELECT COUNT(*) FROM core_memory WHERE user_id=?", (user_id,)).fetchone()[0]
            high = conn.execute("SELECT COUNT(*) FROM core_memory WHERE user_id=? AND importance > 0.7", (user_id,)).fetchone()[0]
            low = conn.execute("SELECT COUNT(*) FROM core_memory WHERE user_id=? AND importance < 0.3", (user_id,)).fetchone()[0]
            return {"total": total, "high_importance": high, "low_importance": low}
        finally:
            conn.close()
