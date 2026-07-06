"""Tests for core/ module — unique tests only."""

from core.reflex import ReflexBuffer


def test_reflex_buffer():
    buf = ReflexBuffer(max_size=5)
    buf.add(role="user", content="Hello", tokens=5)
    buf.add(role="assistant", content="Hi", tokens=3)
    assert buf.size() == 2
    assert buf.get_recent(1)[0].content == "Hi"
