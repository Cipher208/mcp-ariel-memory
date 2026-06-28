"""
Forgetting System - decay, archiving, compression
"""

import logging
import time
from pathlib import Path

from config import config
from shared.connection import AsyncConnectionManager, connection_manager

logger = logging.getLogger(__name__)

ARCHIVE_DIR = Path.home() / ".mcp-ariel-memory" / "archives"


class ForgettingSystem:
    def __init__(self, cm: AsyncConnectionManager = None, layer: str = "user"):
        self._cm = cm or connection_manager
        self.layer = layer
        self.decay_rate = config.get_forgetting("decay_rate") or 0.01
        self.archive_days = config.get_forgetting("archive_threshold_days") or 90
        self.archive_min_importance = config.get_forgetting("archive_min_importance") or 0.3
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    async def decay_importance(self) -> int:
        try:
            now = time.time()
            conn = await self._cm.get("memory.db")
            cursor = await conn.execute(
                """UPDATE core_memory SET importance = MAX(0.01,
                   importance * EXP(-? * (? - updated_at) / 86400))
                   WHERE importance > 0.01""",
                (self.decay_rate, now),
            )
            await conn.commit()
            affected = cursor.rowcount
            if affected > 0:
                logger.info("Decayed %d entries" % affected)
            return affected
        except Exception as e:
            logger.error("Decay failed: %s" % e)
            return 0

    async def archive_old_entries(self) -> int:
        try:
            conn = await self._cm.get("memory.db")
            cutoff = time.time() - (self.archive_days * 86400)
            cursor = await conn.execute(
                "SELECT * FROM core_memory WHERE updated_at < ? AND importance < ?",
                (cutoff, self.archive_min_importance),
            )
            rows = await cursor.fetchall()
            if not rows:
                return 0

            # Use ArchivedMemories instead of manual JSON
            from shared.archived_memories import ArchivedMemories

            am = ArchivedMemories()
            archived_count = 0
            for row in rows:
                await am.archive(
                    user_id=row["user_id"],
                    content="%s=%s" % (row["key"], row["value"]),
                    memory_type="core_memory",
                    importance=row["importance"],
                    original_id=row["entry_id"],
                    reason="inactive_%dd" % self.archive_days,
                )
                archived_count += 1

            ids = [row["entry_id"] for row in rows]
            placeholders = ",".join(["?"] * len(ids))
            await conn.execute("DELETE FROM core_memory WHERE entry_id IN (%s)" % placeholders, ids)
            await conn.commit()
            logger.info("Archived %d entries" % archived_count)
            return archived_count
        except Exception as e:
            logger.error("Archive failed: %s" % e)
            return 0

    async def compress_duplicates(self) -> int:
        try:
            conn = await self._cm.get("memory.db")
            cursor = await conn.execute("SELECT user_id, key, COUNT(*) as cnt FROM core_memory GROUP BY user_id, key HAVING cnt > 1")
            duplicates = await cursor.fetchall()
            removed = 0
            for dup in duplicates:
                await conn.execute(
                    """DELETE FROM core_memory WHERE user_id=? AND key=? AND entry_id NOT IN
                       (SELECT entry_id FROM core_memory WHERE user_id=? AND key=? ORDER BY updated_at DESC LIMIT 1)""",
                    (dup["user_id"], dup["key"], dup["user_id"], dup["key"]),
                )
                changes_cursor = await conn.execute("SELECT changes()")
                changes_row = await changes_cursor.fetchone()
                removed += changes_row[0]
            await conn.commit()
            return removed
        except Exception as e:
            logger.error("Compression failed: %s" % e)
            return 0

    async def cleanup(self) -> dict[str, int]:
        return {
            "decayed": await self.decay_importance(),
            "archived": await self.archive_old_entries(),
            "compressed": await self.compress_duplicates(),
        }
