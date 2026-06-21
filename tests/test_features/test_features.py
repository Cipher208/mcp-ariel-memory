"""Tests for features/ module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_audit_trail():
    from features.audit_trail import AuditTrail
    at = AuditTrail()
    at.log("test_feat", "test_action")
    history = at.get_history("test_feat")
    assert len(history) >= 1


def test_audit_rotation():
    from features.audit_trail import AuditTrail
    at = AuditTrail()
    at.log("test_rot", "action")
    result = at.cleanup_old(retention_days=0)
    assert result >= 0


def test_rate_limiter():
    from features.rate_limiting import RateLimiter
    rl = RateLimiter()
    r = rl.check("test_feat")
    assert r["allowed"] is True
    stats = rl.get_stats("test_feat")
    assert "requests_last_minute" in stats


def test_backup():
    from features.backup import BackupManager
    bm = BackupManager()
    path = bm.backup("test_feat")
    assert path is not None


def test_import_export():
    from features.import_export import ImportExport
    ie = ImportExport()
    path = ie.export_user("test_feat")
    assert path is not None


def test_compression():
    from features.compression import MemoryCompressor
    mc = MemoryCompressor()
    stats = mc.get_stats("test_feat")
    assert "core" in stats
