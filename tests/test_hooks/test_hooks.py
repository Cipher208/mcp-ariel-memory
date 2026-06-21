"""Tests for hooks/ module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_hook_registry():
    from hooks.registry import HookRegistry
    hr = HookRegistry()
    hr.register("test_hook", lambda ctx: {"ok": True})
    result = hr.fire("test_hook", "user", {"data": 1})
    assert result["handler_count"] == 1


def test_user_hooks_importance():
    from hooks.user_hooks import UserHooks
    uh = UserHooks("test_hooks")
    r = uh._importance_gate({"text": "How do I configure Redis?"})
    assert r["importance"] > 0.3


def test_agent_hooks_error():
    from hooks.agent_hooks import AgentHooks
    ah = AgentHooks("test_hooks")
    r = ah._error_occurred({"error": "NullPointerException"})
    assert "node_id" in r
