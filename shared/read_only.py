"""
Read-only режим — replica для dashboard/metrics/ревизии без нагрузки на основную БД.
Копирует данные из основных БД в read-only копии.
"""
import shutil
import sqlite3
import time
import threading
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ReadOnlyReplica:
    """Read-only копия БД для dashboard и metrics."""

    def __init__(self, source_dir: str = None, replica_dir: str = None):
        self.source_dir = Path(source_dir or str(Path.home() / ".mcp-ariel-memory"))
        self.replica_dir = Path(replica_dir or str(Path.home() / ".mcp-ariel-memory" / "replica"))
        self.replica_dir.mkdir(parents=True, exist_ok=True)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._sync_interval = 300  # 5 минут
        self._last_sync = 0.0

    def sync(self) -> Dict[str, int]:
        """Синхронизировать основные БД в read-only копии."""
        db_files = ["core_memory.db", "episodic.db", "sessions.db",
                     "rag.db", "graph.db", "wiki_index.db", "audit.db"]
        synced = {}
        for db_file in db_files:
            src = self.source_dir / db_file
            dst = self.replica_dir / db_file
            if src.exists():
                try:
                    # Используем SQLite backup API для безопасного копирования
                    src_conn = sqlite3.connect(str(src))
                    dst_conn = sqlite3.connect(str(dst))
                    src_conn.backup(dst_conn)
                    dst_conn.close()
                    src_conn.close()
                    synced[db_file] = 1
                except Exception as e:
                    logger.error("Replica sync failed for %s: %s" % (db_file, e))
                    # Fallback: простое копирование
                    try:
                        shutil.copy2(src, dst)
                        synced[db_file] = 1
                    except Exception:
                        synced[db_file] = 0

        self._last_sync = time.time()
        logger.info("Replica synced: %d files" % len(synced))
        return synced

    def start_auto_sync(self, interval_seconds: int = 300):
        """Запустить автоматическую синхронизацию."""
        self._sync_interval = interval_seconds
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Replica auto-sync started (interval=%ds)" % interval_seconds)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _loop(self):
        while self._running:
            try:
                if time.time() - self._last_sync >= self._sync_interval:
                    self.sync()
                time.sleep(60)
            except Exception as e:
                logger.error("Replica sync error: %s" % e)
                time.sleep(300)

    def get_conn(self, db_name: str = "core_memory.db") -> sqlite3.Connection:
        """Получить read-only соединение с репликой."""
        db_path = self.replica_dir / db_name
        if not db_path.exists():
            # Fallback на основную БД
            db_path = self.source_dir / db_name
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def is_ready(self) -> bool:
        """Проверить, что реплика готова к использованию."""
        return (self.replica_dir / "core_memory.db").exists()


# Singleton
read_only_replica = ReadOnlyReplica()
