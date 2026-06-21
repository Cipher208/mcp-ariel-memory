"""
Backup Cron — automatic scheduled backups
"""
import os
import time
import json
import threading
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from config import config

logger = logging.getLogger(__name__)


class BackupCron:
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or str(Path.home() / ".mcp-ariel-memory"))
        self.backup_dir = self.base_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.interval_hours = config.get("backup", "backup_interval_hours") or 24
        self.retention_days = config.get("backup", "backup_retention_days") or 30
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_backup = 0.0
        self._state_file = self.base_dir / ".backup_cron_state.json"
        self._load_state()

    def _load_state(self):
        if self._state_file.exists():
            try:
                state = json.loads(self._state_file.read_text(encoding="utf-8"))
                self._last_backup = state.get("last_backup", 0.0)
            except Exception:
                pass

    def _save_state(self):
        self._state_file.write_text(
            json.dumps({"last_backup": self._last_backup}),
            encoding="utf-8"
        )

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Backup cron started (interval=%dh)" % self.interval_hours)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _loop(self):
        while self._running:
            try:
                now = time.time()
                if now - self._last_backup >= self.interval_hours * 3600:
                    self._do_backup()
                    self._cleanup_old()
                time.sleep(60)
            except Exception as e:
                logger.error("Backup cron error: %s" % e)
                time.sleep(300)

    def _do_backup(self) -> str:
        import shutil
        import uuid
        timestamp = int(time.time())
        name = "auto_%d_%s" % (timestamp, uuid.uuid4().hex[:6])
        dest = self.backup_dir / name
        dest.mkdir(parents=True, exist_ok=True)

        db_files = ["core_memory.db", "episodic.db", "sessions.db", "rag.db", "graph.db", "wiki.db"]
        backed_up = []
        for db_file in db_files:
            src = self.base_dir / db_file
            if src.exists():
                shutil.copy2(src, dest / db_file)
                backed_up.append(db_file)

        manifest = {"name": name, "timestamp": timestamp, "files": backed_up}
        (dest / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        self._last_backup = time.time()
        self._save_state()
        logger.info("Auto-backup created: %s (%d files)" % (name, len(backed_up)))
        return str(dest)

    def _cleanup_old(self):
        import shutil
        cutoff = time.time() - (self.retention_days * 86400)
        removed = 0
        for d in self.backup_dir.iterdir():
            if d.is_dir() and d.stat().st_mtime < cutoff:
                shutil.rmtree(d)
                removed += 1
                logger.info("Removed old backup: %s" % d.name)
        if removed:
            logger.info("Cleaned up %d old backups" % removed)

    def backup_now(self) -> str:
        return self._do_backup()

    def restore(self, backup_name: str) -> Dict[str, Any]:
        import shutil
        src = self.backup_dir / backup_name
        if not src.exists():
            return {"error": "Backup not found: %s" % backup_name}

        manifest_path = src / "manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        else:
            manifest = {"files": [f.name for f in src.glob("*.db")]}

        restored = []
        for db_file in manifest.get("files", []):
            backup_file = src / db_file
            if backup_file.exists():
                shutil.copy2(backup_file, self.base_dir / db_file)
                restored.append(db_file)

        return {"restored": restored, "backup": backup_name}

    def list_backups(self) -> list:
        backups = []
        for d in sorted(self.backup_dir.iterdir(), reverse=True):
            if d.is_dir():
                info = {"name": d.name}
                manifest_path = d / "manifest.json"
                if manifest_path.exists():
                    try:
                        info.update(json.loads(manifest_path.read_text(encoding="utf-8")))
                    except Exception:
                        pass
                backups.append(info)
        return backups

    def status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "interval_hours": self.interval_hours,
            "retention_days": self.retention_days,
            "last_backup": self._last_backup,
            "next_backup": self._last_backup + self.interval_hours * 3600,
            "backup_count": len(list(self.backup_dir.iterdir())),
        }


backup_cron = BackupCron()
