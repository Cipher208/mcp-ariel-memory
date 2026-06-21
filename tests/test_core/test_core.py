"""Tests for core/ module (L1-L4)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_user_remember_recall():
    from core import memory_manager
    mm = memory_manager
    mm.user_memory("test_core").remember("lang", "Python", 0.8)
    results = mm.user_memory("test_core").recall("lang")
    assert len(results) > 0
    assert results[0]["key"] == "lang"


def test_agent_remember_recall():
    from core import memory_manager
    mm = memory_manager
    mm.agent_memory("test_core").remember("rule", "YAGNI", 0.9)
    results = mm.agent_memory("test_core").recall("rule")
    assert len(results) > 0


def test_reflex_buffer():
    from core.reflex import ReflexBuffer
    buf = ReflexBuffer(max_size=5)
    buf.add(role="user", content="Hello", tokens=5)
    buf.add(role="assistant", content="Hi", tokens=3)
    assert buf.size() == 2
    recent = buf.get_recent(1)
    assert len(recent) == 1
    assert recent[0].content == "Hi"


def test_session_store():
    from core.session import SessionStore
    ss = SessionStore()
    sid = ss.create_session("test_core")
    assert sid is not None
    ss.close_session(sid, summary="Test session")
    assert ss.count_sessions("test_core") >= 1


def test_episodic_memory():
    from core.episodic import EpisodicMemory
    ep = EpisodicMemory()
    eid = ep.save("test_core", "Test episode", 0.8, ["tag1"])
    assert eid > 0
    episodes = ep.search_by_tag("test_core", "tag1")
    assert len(episodes) >= 1


def test_core_memory():
    from core.memory import CoreMemory
    cm = CoreMemory()
    cm.save("test_core", "key1", "value1", 0.9)
    entry = cm.get("test_core", "key1")
    assert entry is not None
    assert entry.value == "value1"
    results = cm.search("test_core", "value1")
    assert len(results) > 0
    assert cm.delete("test_core", "key1")
    assert cm.get("test_core", "key1") is None
