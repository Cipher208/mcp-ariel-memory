"""
DB Migrations — простая система миграций схемы.
Версионирование: каждая миграция имеет номер и имя.
При старте проверяется текущая версия и применяются недостающие миграции.
"""
import sqlite3
import logging
import time
from pathlib import Path
from typing import List, Callable, Dict, Any

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent.parent / "migrations"


class Migration:
    def __init__(self, version: int, name: str, up: Callable[[sqlite3.Connection], None]):
        self.version = version
        self.name = name
        self.up = up


def _get_migrations() -> List[Migration]:
    """Реестр всех миграций. Порядок важен — каждая следующая зависит от предыдущей."""
    migrations = []

    def v1_init(conn):
        """Начальная схема — все таблицы."""
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS core_memory (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                importance REAL DEFAULT 0.5,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_core_user ON core_memory(user_id);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_core_user_key ON core_memory(user_id, key);

            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                summary TEXT,
                state_deltas TEXT,
                topics TEXT,
                message_count INTEGER DEFAULT 0,
                started_at REAL NOT NULL,
                ended_at REAL
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

            CREATE TABLE IF NOT EXISTS episodes (
                episode_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                summary TEXT NOT NULL,
                emotional_weight REAL DEFAULT 0.5,
                tags TEXT,
                created_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_episodes_user ON episodes(user_id);

            CREATE TABLE IF NOT EXISTS staging_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'default',
                session_id TEXT NOT NULL,
                event_id TEXT,
                content TEXT NOT NULL,
                importance REAL DEFAULT 0.5,
                metadata TEXT DEFAULT '{}',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_staging_user ON staging_memories(user_id);

            CREATE TABLE IF NOT EXISTS archived_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'default',
                original_id INTEGER,
                content TEXT NOT NULL,
                memory_type TEXT,
                importance REAL,
                archive_reason TEXT NOT NULL,
                archived_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_archived_user ON archived_memories(user_id);

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

            CREATE TABLE IF NOT EXISTS rate_limits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                timestamp REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_rl_user ON rate_limits(user_id);

            CREATE TABLE IF NOT EXISTS embedding_cache (
                text_hash TEXT PRIMARY KEY,
                embedding BLOB NOT NULL,
                model_name TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS migration_log (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at REAL NOT NULL
            );
        """)

    migrations.append(Migration(1, "init_schema", v1_init))

    def v2_add_is_conflict(conn):
        """Добавить is_conflict и conflict_group_id в core_memory."""
        try:
            conn.execute("ALTER TABLE core_memory ADD COLUMN is_conflict INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE core_memory ADD COLUMN conflict_group_id TEXT")
        except sqlite3.OperationalError:
            pass

    migrations.append(Migration(2, "add_conflict_fields", v2_add_is_conflict))

    def v3_add_wiki_source(conn):
        """Добавить source column в wiki таблицы."""
        for table in ["user_wiki", "agent_wiki"]:
            try:
                conn.execute("ALTER TABLE %s ADD COLUMN source TEXT DEFAULT 'manual'" % table)
            except sqlite3.OperationalError:
                pass

    migrations.append(Migration(3, "add_wiki_source", v3_add_wiki_source))

    return migrations


class MigrationManager:
    """Менеджер миграций — применяет недостающие миграции при старте."""

    def __init__(self, db_dir: str = None):
        self.db_dir = Path(db_dir or str(Path.home() / ".mcp-ariel-memory"))
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self._migrations = _get_migrations()

    def _get_version_conn(self) -> sqlite3.Connection:
        db_path = str(self.db_dir / "core_memory.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_current_version(self) -> int:
        conn = self._get_version_conn()
        try:
            try:
                row = conn.execute("SELECT MAX(version) as v FROM migration_log").fetchone()
                return row["v"] if row and row["v"] else 0
            except sqlite3.OperationalError:
                return 0
        finally:
            conn.close()

    def migrate(self) -> Dict[str, Any]:
        """Применить все недостающие миграции."""
        current = self.get_current_version()
        applied = []

        for migration in self._migrations:
            if migration.version <= current:
                continue

            logger.info("Applying migration v%d: %s" % (migration.version, migration.name))
            conn = self._get_version_conn()
            try:
                migration.up(conn)
                conn.execute(
                    "INSERT INTO migration_log (version, name, applied_at) VALUES (?, ?, ?)",
                    (migration.version, migration.name, time.time())
                )
                conn.commit()
                applied.append({"version": migration.version, "name": migration.name})
            except Exception as e:
                logger.error("Migration v%d failed: %s" % (migration.version, e))
                raise
            finally:
                conn.close()

        return {"current_version": current, "applied": applied, "new_version": self.get_current_version()}

    def get_pending(self) -> List[Dict[str, Any]]:
        """Список ожидающих миграций."""
        current = self.get_current_version()
        return [
            {"version": m.version, "name": m.name}
            for m in self._migrations
            if m.version > current
        ]


# Singleton
migration_manager = MigrationManager()
