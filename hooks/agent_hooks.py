"""
Agent Layer Hooks - 12 hooks for agent identity events
"""

from typing import Any

from graph.epistemic import EpistemicGraph
from lifecycle.consolidation import ConsolidationEngine
from lifecycle.forgetting import ForgettingSystem
from rag.conflict import ConflictResolver
from rag.router import RetrievalRouter

from .registry import hook_registry


class AgentHooks:
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.graph = EpistemicGraph(layer="agent")
        self._register_all()

    def _register_all(self):
        hook_registry.register("error_occurred", self._error_occurred)
        hook_registry.register("decision_made", self._decision_made)
        hook_registry.register("self_correction", self._self_correction)
        hook_registry.register("personality_shift", self._personality_shift)
        hook_registry.register("emotion_context", self._emotion_context)
        hook_registry.register("wiki_agent", self._wiki_agent)
        hook_registry.register("consolidation", self._consolidation)
        hook_registry.register("forgetting_ritual", self._forgetting_ritual)
        hook_registry.register("auto_context", self._auto_context)
        hook_registry.register("retrieval_router", self._retrieval_router)
        hook_registry.register("conflict_resolver", self._conflict_resolver)
        hook_registry.register("emotion", self._emotion)

    def _error_occurred(self, ctx: dict[str, Any]) -> dict[str, Any]:
        error = ctx.get("error", "")
        node_id = self.graph.add_node(self.user_id, error, "error_analysis", ["error_pattern"], 0.8)
        return {"action": "error_analyzed", "node_id": node_id}

    def _decision_made(self, ctx: dict[str, Any]) -> dict[str, Any]:
        decision = ctx.get("decision", "")
        rationale = ctx.get("rationale", "")
        node_id = self.graph.add_node(
            self.user_id, f"{decision}: {rationale}", "decision_log", ["decided_because"], 0.7
        )
        return {"action": "decision_logged", "node_id": node_id}

    def _self_correction(self, ctx: dict[str, Any]) -> dict[str, Any]:
        error = ctx.get("error", "")
        fix = ctx.get("fix", "")
        node_id = self.graph.add_node(
            self.user_id, f"Error: {error} → Fix: {fix}", "correction", ["correction_pattern"], 0.6
        )
        return {"action": "correction_logged", "node_id": node_id}

    def _personality_shift(self, ctx: dict[str, Any]) -> dict[str, Any]:
        shift = ctx.get("shift", "")
        node_id = self.graph.add_node(
            self.user_id, shift, "personality_evolution", ["personality_trait", "evolved_to"], 0.9
        )
        return {"action": "personality_evolved", "node_id": node_id}

    def _emotion_context(self, ctx: dict[str, Any]) -> dict[str, Any]:
        emotion = ctx.get("emotion", "")
        context = ctx.get("context", "")
        node_id = self.graph.add_node(
            self.user_id, f"{emotion} in: {context}", "emotional_context", ["felt_in_context"], 0.6
        )
        return {"action": "emotion_logged", "node_id": node_id}

    def _wiki_agent(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"action": "wiki_sync", "summary": ctx.get("summary", "")}

    def _consolidation(self, ctx: dict[str, Any]) -> dict[str, Any]:
        staging = ctx.get("staging_items", [])
        engine = ConsolidationEngine()
        result = engine.consolidate_staging(self.user_id, staging, min_importance=0.6)
        return {"action": "agent_consolidated", **result}

    def _forgetting_ritual(self, ctx: dict[str, Any]) -> dict[str, Any]:
        fs = ForgettingSystem()
        return fs.cleanup()

    def _auto_context(self, ctx: dict[str, Any]) -> dict[str, Any]:
        query = ctx.get("query", "")
        router = RetrievalRouter(layer="agent", user_id=self.user_id)
        result = router.route(query)
        return {"context": result.context, "strategy": result.strategy.value}

    def _retrieval_router(self, ctx: dict[str, Any]) -> dict[str, Any]:
        query = ctx.get("query", "")
        router = RetrievalRouter(layer="agent", user_id=self.user_id)
        result = router.route(query)
        return {"strategy": result.strategy.value, "confidence": result.confidence}

    def _conflict_resolver(self, ctx: dict[str, Any]) -> dict[str, Any]:
        content = ctx.get("content", "")
        resolver = ConflictResolver()
        return resolver.check(self.user_id, content)

    def _emotion(self, ctx: dict[str, Any]) -> dict[str, Any]:
        emotion = ctx.get("emotion", "")
        node_id = self.graph.add_node(self.user_id, emotion, "emotional_context", ["felt_in_context"], 0.5)
        return {"action": "emotion_recorded", "node_id": node_id}
