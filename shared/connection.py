"""
AsyncConnectionManager — единый менеджер соединений SQLite.

Правила:
- Один коннект на файл БД (не пул — пул для SQLite антипаттерн)
- WAL + busy_timeout для конкурентности
- Нативный async через aiosqlite (уже в зависимостях)
- row_factory = aiosqlite.Row (совместим с sqlite3.Row)

Использование:
    cm = AsyncConnectionManager()
    conn = await cm.get("core_memory.db")
    cur = await conn.execute("SELECT * FROM users WHERE id=?", (uid,))
    row = await cur.fetchone()
"""

import os
import logging
from pathlib import Path
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)

_DEFAULT_DIR = os.environ.get(
    "MCP_MEMORY_DATA_DIR",
    str(Path.home() / ".mcp-ariel-memory"),
)


class AsyncConnectionManager:
    """Один коннект на файл БД. Без пула — с очередью внутри aiosqlite."""

    def __init__(self, base_dir: str = ""):
        self.base_dir = Path(base_dir or _DEFAULT_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._conns: dict[str, aiosqlite.Connection] = {}

    # ------------------------------------------------------------------
    # Основное API
    # ------------------------------------------------------------------

    async def get(self, db_name: str = "core_memory.db") -> aiosqlite.Connection:
        """Вернуть (или создать) коннект к `db_name`."""
        if db_name in self._conns:
            conn = self._conns[db_name]
            # проверить что коннект жив
            try:
                await conn.execute("SELECT 1")
                return conn
            except Exception:
                logger.warning("connection %s stale, reopening", db_name)
                del self._conns[db_name]

        db_path = str(self.base_dir / db_name)
        conn = await aiosqlite.connect(db_path)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA busy_timeout=5000")
        await conn.execute("PRAGMA synchronous=NORMAL")
        # внешние ключи для целостности
        await conn.execute("PRAGMA foreign_keys=ON")

        self._conns[db_name] = conn
        logger.debug("opened connection %s (%s)", db_name, db_path)
        return conn

    async def close_all(self):
        """Закрыть все открытые коннекты (при shutdown)."""
        for name, conn in self._conns.items():
            try:
                await conn.close()
                logger.debug("closed connection %s", name)
            except Exception:
                pass
        self._conns.clear()

    def stats(self) -> dict:
        return {
            "connections": len(self._conns),
            "dbs": list(self._conns.keys()),
        }

    # ------------------------------------------------------------------
    # Хелперы для миграций и init-db
    # ------------------------------------------------------------------

    async def execute_script(self, db_name: str, script: str):
        """Выполнить SQL-скрипт (например CREATE TABLE) и закоммитить."""
        conn = await self.get(db_name)
        await conn.executescript(script)
        await conn.commit()

    async def table_exists(self, db_name: str, table: str) -> bool:
        """Проверить, существует ли таблица."""
        conn = await self.get(db_name)
        cur = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        )
        row = await cur.fetchone()
        return row is not None

    async def vacuum(self, db_name: str):
        """VACUUM — освободить место после массовых удалений."""
        conn = await self.get(db_name)
        await conn.execute("VACUUM")
        await conn.commit()


# Глобальный экземпляр — используется по умолчанию
connection_manager = AsyncConnectionManager()


# ------------------------------------------------------------------
# Пример: как перевести любой модуль на AsyncConnectionManager
# ------------------------------------------------------------------
#
# ДО (было):
#
#   class CoreMemory:
#       def __init__(self, db_path=None):
#           self.db_path = db_path or str(Path.home() / ".mcp-ariel-memory" / "core_memory.db")
#           self._init_db()
#
#       def _get_conn(self):
#           conn = sqlite3.connect(self.db_path)
#           conn.row_factory = sqlite3.Row
#           conn.execute("PRAGMA journal_mode=WAL")
#           return conn
#
# ПОСЛЕ (стало):
#
#   class CoreMemory:
#       def __init__(self, cm: AsyncConnectionManager = None):
#           self._cm = cm or connection_manager
#
#       async def _init_db(self):
#           await self._cm.execute_script("core_memory.db", """
#               CREATE TABLE IF NOT EXISTS core_memory (...)
#           """)
#
#       async def save(self, user_id, key, value, importance=0.5):
#           conn = await self._cm.get("core_memory.db")
#           await conn.execute("UPSERT ...", (user_id, key, value, importance))
#           await conn.commit()