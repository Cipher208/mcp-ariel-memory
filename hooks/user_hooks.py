"""
User Layer Hooks - 12 hooks for user memory events
"""

from typing import Any, Optional

from lifecycle.emotion_trigger import EmotionTrigger

from .registry import hook_registry
from .shared import (
    auto_context,
    conflict_resolver,
    consolidation,
    forgetting_ritual,
    retrieval_router,
)


class UserHooks:
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.emotion_trigger = EmotionTrigger()
        self._register_all()

    def _register_all(self):
        hook_registry.register("message_received", self._message_received)
        hook_registry.register("message_sent", self._message_sent)
        hook_registry.register("state_delta", self._state_delta)
        hook_registry.register("consolidation", self._consolidation)
        hook_registry.register("emotion_trigger", self._emotion_trigger)
        hook_registry.register("nightly", self._nightly)
        hook_registry.register("importance_gate", self._importance_gate)
        hook_registry.register("auto_context", self._auto_context)
        hook_registry.register("forgetting_ritual", self._forgetting_ritual)
        hook_registry.register("retrieval_router", self._retrieval_router)
        hook_registry.register("conflict_resolver", self._conflict_resolver)
        hook_registry.register("dream_buffer", self._dream_buffer)

    def _message_received(self, ctx: dict[str, Any]) -> dict[str, Any]:
        text = ctx.get("text", "")
        importance = self._calculate_importance(text)
        return {"action": "store_to_l1", "importance": importance, "text": text[:100]}

    def _message_sent(self, ctx: dict[str, Any]) -> dict[str, Any]:
        text = ctx.get("text", "")
        return {"action": "store_to_l1", "role": "assistant", "text": text[:100]}

    def _state_delta(self, ctx: dict[str, Any]) -> dict[str, Any]:
        delta = ctx.get("delta", {})
        if delta:
            return {"action": "save_episode", "summary": f"State changed: {list(delta.keys())}", "weight": 0.4}
        return {"action": "skip"}

    def _consolidation(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return consolidation(ctx, self.user_id)

    def _emotion_trigger(self, ctx: dict[str, Any]) -> dict[str, Any]:
        text = ctx.get("text", "")
        should, reason, weight = self.emotion_trigger.should_save(text)
        if should:
            return {"action": "save_episode", "reason": reason, "weight": weight}
        return {"action": "skip"}

    def _nightly(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"action": "create_diary", "summary": ctx.get("daily_summary", "")}

    def _importance_gate(self, ctx: dict[str, Any]) -> dict[str, Any]:
        text = ctx.get("text", "")
        kind = ctx.get("memory_kind")
        score = self._calculate_importance(text, kind)
        return {"importance": score, "bypass": score < 0.3}

    def _auto_context(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return auto_context(ctx, self.user_id)

    def _forgetting_ritual(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return forgetting_ritual(ctx)

    def _retrieval_router(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return retrieval_router(ctx, self.user_id, include_count=True)

    def _conflict_resolver(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return conflict_resolver(ctx, self.user_id)

    def _dream_buffer(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"action": "add_to_staging", "content": ctx.get("text", "")}

    def _calculate_importance(self, text: str, memory_kind: Optional[str] = None) -> float:
        from shared.memory_types import default_importance

        if not text:
            return 0.0

        # Start with type-based importance if kind specified
        if memory_kind:
            score = default_importance(memory_kind)
        else:
            score = 0.3

        # Length heuristics
        if len(text) > 15:
            score += 0.15
        if len(text) > 100:
            score += 0.1
        # Semantic keywords
        keywords = ["important", "critical", "urgent", "preference", "favorite", "hate", "love"]
        for kw in keywords:
            if kw in text.lower():
                score += 0.1
                break
        # Structure signals
        if "?" in text:
            score += 0.15
        if text.count("\n") > 2:
            score += 0.1
        # Emotional markers
        if any(c in text for c in ["!", "?"]):
            score += 0.05
        return min(1.0, score)
