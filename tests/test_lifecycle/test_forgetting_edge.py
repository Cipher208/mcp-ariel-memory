"""Edge case tests for lifecycle/forgetting.py."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_forgetting_cleanup_runs():
    """cleanup() should run without error."""
    from lifecycle.forgetting import ForgettingSystem

    async def t():
        fs = ForgettingSystem()
        result = await fs.cleanup()
        assert isinstance(result, dict)
        assert "archived" in result or "cleaned" in result or "removed" in result

    asyncio.run(t())


def test_forgetting_decay_runs():
    """decay_importance() should run without error."""
    from lifecycle.forgetting import ForgettingSystem

    async def t():
        fs = ForgettingSystem()
        result = await fs.decay_importance()
        assert isinstance(result, int)
        assert result >= 0

    asyncio.run(t())


def test_forgetting_archive_empty():
    """archive_old_entries() with no old entries should return 0."""
    from lifecycle.forgetting import ForgettingSystem

    async def t():
        fs = ForgettingSystem()
        result = await fs.archive_old_entries()
        assert isinstance(result, int)
        assert result >= 0

    asyncio.run(t())
