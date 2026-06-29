"""Tests for MCP server and tools — async."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_mcp_tools_count():
    from mcp_server import mcp

    tools = mcp._tool_manager.list_tools()
    assert len(tools) >= 15


def test_mcp_tools_are_async():
    import inspect

    from mcp_server import mcp

    tools = mcp._tool_manager.list_tools()
    for tool in tools:
        assert inspect.iscoroutinefunction(tool.fn), f"{tool.name} is not async"
