"""
DB Migrations — async, unified memory.db
Все таблицы в одном файле. wiki/graph/audit можно вынести позже при нагрузке.
"""
import sqlite3
import logging
import time
from pathlib import Path
from typing import List, Callable, Dict, Any, Optional
from shared.connection import AsyncConnectionManager, connection_manager

logger = logging.getLogger(__name__)

DB_NAME = "memory.db"


class Migration:
    def __init__(self, version: int, name: str, up: Callable):
        self.version = version
        self.name = name
        self.up = up


def _get_migrations() -> List[Migration]:
    migrations = []

    async def v1_init(conn):
        """Все таблицы в одном memory.db."""
        await conn.executescript("""
            -- === L2-L4 Core ===
            CREATE TABLE IF NOT EXISTS core_memory (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL,
                importance REAL DEFAULT 0.5, is_conflict INTEGER DEFAULT 0,
                conflict_group_id TEXT, created_at REAL NOT NULL, updated_at REAL NOT NULL
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

            -- === Staging + Archived ===
            CREATE TABLE IF NOT EXISTS staging_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'default', session_id TEXT NOT NULL,
                event_id TEXT, content TEXT NOT NULL, importance REAL DEFAULT 0.5,
                metadata TEXT DEFAULT '{}', created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS archived_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'default', original_id INTEGER,
                content TEXT NOT NULL, memory_type TEXT, importance REAL,
                archive_reason TEXT NOT NULL, archived_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            -- === Audit ===
            CREATE TABLE IF NOT EXISTS audit_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL, action TEXT NOT NULL, layer TEXT,
                target_id TEXT, details TEXT, timestamp REAL NOT NULL
            );

            -- === Rate Limit ===
            CREATE TABLE IF NOT EXISTS rate_limits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL, timestamp REAL NOT NULL
            );

            -- === Embeddings ===
            CREATE TABLE IF NOT EXISTS embedding_cache (
                text_hash TEXT PRIMARY KEY, embedding BLOB NOT NULL,
                model_name TEXT NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            -- === RAG ===
            CREATE TABLE IF NOT EXISTS rag_pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                layer TEXT NOT NULL DEFAULT 'user', user_id TEXT NOT NULL DEFAULT 'default',
                title TEXT NOT NULL, path TEXT, content TEXT NOT NULL,
                sha256_hash TEXT, wiki_type TEXT,
                created_at REAL DEFAULT (strftime('%s','now')),
                updated_at REAL DEFAULT (strftime('%s','now'))
            );
            CREATE TABLE IF NOT EXISTS rag_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page_id INTEGER NOT NULL, chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL, embedding BLOB
            );
            CREATE TABLE IF NOT EXISTS rag_relations (
                source_id INTEGER NOT NULL, target_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL DEFAULT 'elaborates',
                weight REAL DEFAULT 0.8,
                PRIMARY KEY (source_id, target_id, relation_type)
            );
            CREATE INDEX IF NOT EXISTS idx_rag_user ON rag_pages(user_id);

            -- === Graph ===
            CREATE TABLE IF NOT EXISTS epi_nodes (
                node_id INTEGER PRIMARY KEY AUTOINCREMENT,
                layer TEXT NOT NULL DEFAULT 'user',
                user_id TEXT NOT NULL, content TEXT NOT NULL,
                node_type TEXT NOT NULL, tags TEXT,
                confidence REAL DEFAULT 0.5, created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS epi_edges (
                source_id INTEGER NOT NULL, target_id INTEGER NOT NULL,
                relation TEXT NOT NULL, weight REAL DEFAULT 0.8,
                created_at REAL NOT NULL,
                PRIMARY KEY (source_id, target_id, relation)
            );
            CREATE TABLE IF NOT EXISTS temporal_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL, event_type TEXT NOT NULL,
                content TEXT NOT NULL, timestamp REAL NOT NULL,
                importance REAL DEFAULT 0.5, metadata TEXT
            );
            CREATE TABLE IF NOT EXISTS temporal_links (
                from_event INTEGER NOT NULL, to_event INTEGER NOT NULL,
                link_type TEXT NOT NULL DEFAULT 'follows',
                strength REAL DEFAULT 0.5,
                PRIMARY KEY (from_event, to_event, link_type)
            );

            -- === Wiki ===
            CREATE TABLE IF NOT EXISTS user_wiki (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL, wiki_type TEXT NOT NULL,
                title TEXT NOT NULL, content TEXT NOT NULL,
                tags TEXT, importance REAL DEFAULT 0.5,
                source TEXT DEFAULT 'manual',
                created_at REAL NOT NULL, updated_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS agent_wiki (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL, wiki_type TEXT NOT NULL,
                title TEXT NOT NULL, content TEXT NOT NULL,
                tags TEXT, importance REAL DEFAULT 0.5,
                source TEXT DEFAULT 'manual',
                created_at REAL NOT NULL, updated_at REAL NOT NULL
            );

            -- === FileWiki ===
            CREATE TABLE IF NOT EXISTS wiki_index (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                layer TEXT NOT NULL, wiki_type TEXT NOT NULL,
                title TEXT NOT NULL, file_path TEXT NOT NULL,
                tags TEXT, importance REAL DEFAULT 0.5,
                content TEXT DEFAULT '', content_hash TEXT,
                created_at REAL NOT NULL, updated_at REAL NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_wiki_path ON wiki_index(file_path);

            -- === FTS5 indexes ===
            CREATE VIRTUAL TABLE IF NOT EXISTS rag_fts USING fts5(
                title, content, wiki_type, content=rag_pages, content_rowid=id
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS user_wiki_fts USING fts5(
                title, content, wiki_type, tags, content=user_wiki, content_rowid=entry_id
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS agent_wiki_fts USING fts5(
                title, content, wiki_type, tags, content=agent_wiki, content_rowid=entry_id
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS wiki_fts USING fts5(
                title, content, wiki_type, tags, content=wiki_index, content_rowid=entry_id
            );

            -- === Conflict tracking ===
            CREATE TABLE IF NOT EXISTS memory_conflicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL, content TEXT NOT NULL,
                is_conflict INTEGER DEFAULT 0, conflict_group_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            -- === Migration log ===
            CREATE TABLE IF NOT EXISTS migration_log (
                version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at REAL NOT NULL
            );
        """)
    migrations.append(Migration(1, "init_unified_schema", v1_init))

    return migrations


class MigrationManager:
    def __init__(self, cm: Optional[AsyncConnectionManager] = None):
        self._cm = cm or connection_manager
        self._migrations = _get_migrations()

    async def get_current_version(self) -> int:
        conn = await self._cm.get(DB_NAME)
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
            conn = await self._cm.get(DB_NAME)
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


migration_manager = MigrationManager()
