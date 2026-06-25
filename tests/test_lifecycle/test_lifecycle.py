"""Tests for lifecycle/ module — async."""
import sys
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_forgetting_cleanup():
    from lifecycle.forgetting import ForgettingSystem
    async def t():
        fs = ForgettingSystem()
        stats = await fs.cleanup()
        assert "archived" in stats
    asyncio.run(t())


def test_emotion_trigger():
    from lifecycle.emotion_trigger import EmotionTrigger
    et = EmotionTrigger()
    should, reason, weight = et.should_save("I love this!")
    assert should is True
    should2, _, _ = et.should_save("ok")
    assert should2 is False


def test_consolidation():
    from lifecycle.consolidation import ConsolidationEngine
    async def t():
        ce = ConsolidationEngine()
        result = await ce.consolidate_staging("test_lc", [{"content": "test", "importance": 0.9}], 0.7)
        assert result["promoted"] == 1
    asyncio.run(t())
