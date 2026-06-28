"""Tests for MCP server and tools — async."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_mcp_tools_count():
    from mcp_server import mcp

    tools = mcp._tool_manager.list_tools()
    assert len(tools) >= 20


def test_mcp_tools_are_async():
    import inspect

    from mcp_server import memory_agent_remember, memory_user_remember

    assert inspect.iscoroutinefunction(memory_user_remember)
    assert inspect.iscoroutinefunction(memory_agent_remember)


def test_backward_compat():
    from server import MemoryMCPServer

    s = MemoryMCPServer()
    r = s.call("memory.user.remember", user_id="test_mcp", key="k", value="v")
    assert r.get("status") == "ok" or "entry_id" in r
