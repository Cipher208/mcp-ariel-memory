# Backup

## Features

- Automatic backups with configurable cron
- Jitter to prevent thundering herd
- Export/import for migration
- Backup rotation (old backups cleaned up)

## Usage

```python
from features.backup_cron import BackupCron

cron = BackupCron()
await cron.start()  # Starts background backup daemon
```

## Manual Backup

```python
from features.backup import BackupManager

bm = BackupManager()
backup_name = await bm.create_backup()
backups = await bm.list_backups()
await bm.restore(backup_name)
```
