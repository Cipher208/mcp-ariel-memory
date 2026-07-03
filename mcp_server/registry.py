"""Tool registry — breaks circular imports between server.py, tools_layer.py, tools_ops.py.

Tools register themselves here. server.py pulls from here and applies @mcp.tool().
"""

from mcp.server.fastmcp import Context

_tools: dict[str, callable] = {}


def _get_ctx(ctx: Context):
    """Extract AppContext from FastMCP lifespan context."""
    return ctx.request_context.lifespan_context


def register_tool(name: str, func: callable):
    _tools[name] = func


def get_all_tools() -> dict[str, callable]:
    return dict(_tools)
