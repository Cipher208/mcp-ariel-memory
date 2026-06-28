"""Tests for features/ module — async."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_audit_trail():
    from features.audit_trail import AuditTrail

    async def t():
        at = AuditTrail()
        await at.log("test_feat", "test_action")
        history = await at.get_history("test_feat")
        assert len(history) >= 1

    asyncio.run(t())


def test_audit_rotation():
    from features.audit_trail import AuditTrail

    async def t():
        at = AuditTrail()
        await at.log("test_rot", "action")
        result = await at.cleanup_old(retention_days=0)
        assert result >= 0

    asyncio.run(t())


def test_rate_limiter():
    from features.rate_limiting import RateLimiter

    async def t():
        rl = RateLimiter()
        r = await rl.check("test_feat")
        assert r["allowed"] is True
        stats = await rl.get_stats("test_feat")
        assert "requests_last_minute" in stats

    asyncio.run(t())


def test_backup():
    from features.backup import BackupManager

    async def t():
        bm = BackupManager()
        path = await bm.backup("test_feat")
        assert path is not None

    asyncio.run(t())


def test_import_export():
    from features.import_export import ImportExport

    async def t():
        ie = ImportExport()
        path = await ie.export_user("test_feat")
        assert path is not None

    asyncio.run(t())


def test_compression():
    from features.compression import MemoryCompressor

    async def t():
        mc = MemoryCompressor()
        stats = await mc.get_stats("test_feat")
        assert "core" in stats

    asyncio.run(t())
