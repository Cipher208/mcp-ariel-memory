"""
Backup Manager - automatic backup and restore
"""
import shutil
import time
import json
from pathlib import Path
from typing import Dict, Any, List
from config import config


class BackupManager:
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or str(Path.home() / ".mcp-ariel-memory"))
        self.backup_dir = self.base_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.retention_days = config.get("backup", "backup_retention_days") or 30

    def backup(self, label: str = None) -> str:
        timestamp = int(time.time())
        name = label or f"backup_{timestamp}"
        dest = self.backup_dir / name
        dest.mkdir(parents=True, exist_ok=True)

        db_files = ["core_memory.db", "episodic.db", "sessions.db", "rag.db", "graph.db", "wiki.db"]
        for db_file in db_files:
            src = self.base_dir / db_file
            if src.exists():
                shutil.copy2(src, dest / db_file)

        manifest = {
            "name": name,
            "timestamp": timestamp,
            "files": [f for f in db_files if (self.base_dir / f).exists()],
        }
        (dest / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return str(dest)

    def restore(self, backup_name: str) -> Dict[str, Any]:
        src = self.backup_dir / backup_name
        if not src.exists():
            return {"error": f"Backup {backup_name} not found"}

        manifest_path = src / "manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        else:
            manifest = {"files": [f.name for f in src.glob("*.db")]}

        restored = []
        for db_file in manifest.get("files", []):
            backup_file = src / db_file
            if backup_file.exists():
                dest = self.base_dir / db_file
                shutil.copy2(backup_file, dest)
                restored.append(db_file)

        return {"restored": restored, "backup": backup_name}

    def list_backups(self) -> List[Dict[str, Any]]:
        backups = []
        for d in sorted(self.backup_dir.iterdir(), reverse=True):
            if d.is_dir():
                manifest_path = d / "manifest.json"
                info = {"name": d.name}
                if manifest_path.exists():
                    info.update(json.loads(manifest_path.read_text(encoding="utf-8")))
                backups.append(info)
        return backups

    def cleanup_old(self) -> int:
        cutoff = time.time() - (self.retention_days * 86400)
        removed = 0
        for d in self.backup_dir.iterdir():
            if d.is_dir() and d.stat().st_mtime < cutoff:
                shutil.rmtree(d)
                removed += 1
        return removed
