"""
Migrations — async version tracking for schema changes
"""
import sqlite3
import logging
import time
from pathlib import Path
from typing import List, Callable, Dict, Any, Optional
from shared.connection import AsyncConnectionManager, connection_manager

logger = logging.getLogger(__name__)


class Migration:
    def __init__(self, version: int, name: str, up: Callable):
        self.version = version
        self.name = name
        self.up = up


def _get_migrations() -> List[Migration]:
    migrations = []

    async def v1_init(conn):
        """Начальная схема — core_memory.db.
        staging_memories и archived_memories создаются в cognitive.db через _init_db().
        """
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS core_memory (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL,
                importance REAL DEFAULT 0.5, created_at REAL NOT NULL, updated_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_core_user ON core_memory(user_id);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_core_user_key ON core_memory(user_id, key);

            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, summary TEXT,
                state_deltas TEXT, topics TEXT, message_count INTEGER DEFAULT 0,
                started_at REAL NOT NULL, ended_at REAL
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

            CREATE TABLE IF NOT EXISTS episodes (
                episode_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL, summary TEXT NOT NULL,
                emotional_weight REAL DEFAULT 0.5, tags TEXT, created_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_episodes_user ON episodes(user_id);

            CREATE TABLE IF NOT EXISTS audit_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL, action TEXT NOT NULL, layer TEXT,
                target_id TEXT, details TEXT, timestamp REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS rate_limits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL, timestamp REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS embedding_cache (
                text_hash TEXT PRIMARY KEY, embedding BLOB NOT NULL,
                model_name TEXT NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS migration_log (
                version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at REAL NOT NULL
            );
        """)
    migrations.append(Migration(1, "init_schema", v1_init))

    async def v2_add_conflict(conn):
        for sql in [
            "ALTER TABLE core_memory ADD COLUMN is_conflict INTEGER DEFAULT 0",
            "ALTER TABLE core_memory ADD COLUMN conflict_group_id TEXT",
        ]:
            try:
                await conn.execute(sql)
            except sqlite3.OperationalError:
                pass
    migrations.append(Migration(2, "add_conflict_fields", v2_add_conflict))

    async def v3_add_wiki_source(conn):
        for table in ["user_wiki", "agent_wiki"]:
            try:
                await conn.execute("ALTER TABLE %s ADD COLUMN source TEXT DEFAULT 'manual'" % table)
            except sqlite3.OperationalError:
                pass
    migrations.append(Migration(3, "add_wiki_source", v3_add_wiki_source))

    return migrations


class MigrationManager:
    def __init__(self, cm: Optional[AsyncConnectionManager] = None):
        self._cm = cm or connection_manager
        self._migrations = _get_migrations()

    async def get_current_version(self) -> int:
        conn = await self._cm.get("core_memory.db")
        try:
            row = await (await conn.execute("SELECT MAX(version) as v FROM migration_log")).fetchone()
            return row["v"] if row and row["v"] else 0
        except sqlite3.OperationalError:
            return 0

    async def migrate(self) -> Dict[str, Any]:
        current = await self.get_current_version()
        applied = []
        for migration in self._migrations:
            if migration.version <= current:
                continue
            logger.info("Applying migration v%d: %s" % (migration.version, migration.name))
            conn = await self._cm.get("core_memory.db")
            await migration.up(conn)
            await conn.execute(
                "INSERT INTO migration_log (version, name, applied_at) VALUES (?, ?, ?)",
                (migration.version, migration.name, time.time()),
            )
            await conn.commit()
            applied.append({"version": migration.version, "name": migration.name})
        return {"current_version": current, "applied": applied, "new_version": await self.get_current_version()}

    async def get_pending(self) -> List[Dict[str, Any]]:
        current = await self.get_current_version()
        return [{"version": m.version, "name": m.name} for m in self._migrations if m.version > current]


# Singleton
migration_manager = MigrationManager()
