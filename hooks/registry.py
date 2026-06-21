"""
Hook Registry - central dispatch for all hooks
"""
import logging
from typing import Dict, Any, Callable, List
from config import config

logger = logging.getLogger(__name__)


class HookRegistry:
    def __init__(self):
        self._hooks: Dict[str, List[Callable]] = {}

    def register(self, hook_name: str, handler: Callable):
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        self._hooks[hook_name].append(handler)

    def fire(self, hook_name: str, layer: str, context: Dict[str, Any]) -> Dict[str, Any]:
        known_user = {"message_received","message_sent","state_delta","consolidation","emotion_trigger","nightly","importance_gate","auto_context","forgetting_ritual","retrieval_router","conflict_resolver","dream_buffer"}
        known_agent = {"error_occurred","decision_made","self_correction","personality_shift","emotion_context","wiki_agent","consolidation","forgetting_ritual","auto_context","retrieval_router","conflict_resolver","emotion"}

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

    def list_hooks(self) -> Dict[str, int]:
        return {name: len(handlers) for name, handlers in self._hooks.items()}


# Global instance
hook_registry = HookRegistry()
