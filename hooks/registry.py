"""
Hook Registry - central dispatch for all hooks
"""

import inspect
import logging
from collections.abc import Callable
from typing import Any

from config import config

logger = logging.getLogger(__name__)


def _discover_hook_names(cls) -> set[str]:
    """Auto-discover hook names from a class by inspecting its methods.

    Methods starting with a single underscore (not dunder) are hook handlers.
    The hook name is the method name without the leading underscore.
    """
    return {
        name.lstrip("_")
        for name, _ in inspect.getmembers(cls, predicate=inspect.isfunction)
        if name.startswith("_") and not name.startswith("__")
    }


class HookRegistry:
    def __init__(self):
        self._hooks: dict[str, list[Callable]] = {}

    def register(self, hook_name: str, handler: Callable):
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        self._hooks[hook_name].append(handler)

    def fire(self, hook_name: str, layer: str, context: dict[str, Any]) -> dict[str, Any]:
        # Lazy import to avoid circular dependency at module load time
        from hooks.agent_hooks import AgentHooks
        from hooks.user_hooks import UserHooks

        known_user = _discover_hook_names(UserHooks)
        known_agent = _discover_hook_names(AgentHooks)

        if hook_name in known_user or hook_name in known_agent:
            if not config.is_hook_enabled(layer, hook_name):
                return {"skipped": True, "reason": "hook_disabled"}

        handlers = self._hooks.get(hook_name, [])
        if not handlers:
            return {"skipped": True, "reason": "no_handlers"}

        results = []
        for handler in handlers:
            try:
                result = handler(context)
                results.append(result)
            except Exception as e:
                logger.error("Hook %s failed: %s" % (hook_name, e))
                results.append({"error": str(e)})

        return {"results": results, "handler_count": len(handlers)}

    def list_hooks(self) -> dict[str, int]:
        return {name: len(handlers) for name, handlers in self._hooks.items()}


# Global instance
hook_registry = HookRegistry()
