"""
User Layer Hooks - 12 hooks for user memory events
"""
import time
from typing import Dict, Any
from core.reflex import ReflexBuffer
from lifecycle.emotion_trigger import EmotionTrigger
from lifecycle.consolidation import ConsolidationEngine
from lifecycle.forgetting import ForgettingSystem
from rag.router import RetrievalRouter
from rag.conflict import ConflictResolver
from .registry import hook_registry


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

    def _message_received(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        text = ctx.get("text", "")
        importance = self._calculate_importance(text)
        return {"action": "store_to_l1", "importance": importance, "text": text[:100]}

    def _message_sent(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        text = ctx.get("text", "")
        return {"action": "store_to_l1", "role": "assistant", "text": text[:100]}

    def _state_delta(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        delta = ctx.get("delta", {})
        if delta:
            return {"action": "save_episode", "summary": f"State changed: {list(delta.keys())}", "weight": 0.4}
        return {"action": "skip"}

    def _consolidation(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        staging = ctx.get("staging_items", [])
        engine = ConsolidationEngine()
        result = engine.consolidate_staging(self.user_id, staging)
        return {"action": "consolidated", **result}

    def _emotion_trigger(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        text = ctx.get("text", "")
        should, reason, weight = self.emotion_trigger.should_save(text)
        if should:
            return {"action": "save_episode", "reason": reason, "weight": weight}
        return {"action": "skip"}

    def _nightly(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        return {"action": "create_diary", "summary": ctx.get("daily_summary", "")}

    def _importance_gate(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        text = ctx.get("text", "")
        score = self._calculate_importance(text)
        return {"importance": score, "bypass": score < 0.3}

    def _auto_context(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        query = ctx.get("query", "")
        router = RetrievalRouter(user_id=self.user_id)
        result = router.route(query)
        return {"context": result.context, "strategy": result.strategy.value}

    def _forgetting_ritual(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        fs = ForgettingSystem()
        return fs.cleanup()

    def _retrieval_router(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        query = ctx.get("query", "")
        router = RetrievalRouter(user_id=self.user_id)
        result = router.route(query)
        return {"strategy": result.strategy.value, "confidence": result.confidence, "count": len(result.context)}

    def _conflict_resolver(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        content = ctx.get("content", "")
        resolver = ConflictResolver()
        return resolver.check(self.user_id, content)

    def _dream_buffer(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        return {"action": "add_to_staging", "content": ctx.get("text", "")}

    def _calculate_importance(self, text: str) -> float:
        if not text:
            return 0.0
        score = 0.3
        if len(text) > 15:
            score += 0.2
        if len(text) > 100:
            score += 0.1
        if "?" in text:
            score += 0.2
        if text.count("\n") > 2:
            score += 0.1
        return min(1.0, score)
