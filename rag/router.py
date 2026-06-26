"""
Retrieval Router — async routes queries to the right memory strategy
"""
from enum import Enum
from typing import Any, Dict, List
from .engine import RAGEngine


class Strategy(str, Enum):
    L1_BUFFER = "l1_buffer"
    SEMANTIC = "semantic"
    GRAPH = "graph"
    WIKI = "wiki"


class RouterResult:
    def __init__(self, strategy: Strategy, context: List[Dict[str, Any]], confidence: float):
        self.strategy = strategy
        self.context = context
        self.confidence = confidence


class RetrievalRouter:
    def __init__(self, layer: str = "user", user_id: str = "default"):
        self.layer = layer
        self.user_id = user_id
        self._rag = RAGEngine(layer=layer)
        self._persona_keywords = {"кто ты", "расскажи о себе", "как тебя зовут"}
        self._recent_keywords = {"это", "почему", "как", "только что", "ранее"}
        self._wiki_keywords = {
            "документация", "настроить", "архитектура", "баг", "конфиг",
            "функция", "класс", "модуль", "сервис", "api", "handler",
        }
        self._graph_keywords = {
            "связи", "связано", "relation", "graph", "граф",
            "паттерн", "ошибка", "решение", "почему выбрал",
            "error_pattern", "decision", "learned",
        }

    async def route(self, query: str, recent_context: List[Dict] = None) -> RouterResult:
        q = query.lower()

        if self._is_recent_query(q) and recent_context:
            return RouterResult(Strategy.L1_BUFFER, recent_context, 0.9)

        if self._is_wiki_query(q):
            results = await self._rag.search_rrf(query, self.user_id, limit=3)
            if results:
                page_id = results[0]["id"]
                relations = await self._rag.get_relations(page_id, depth=1)
                if relations:
                    results.append({
                        "title": "Relations",
                        "content": "\n".join([f"- {r['title']} [{r['relation']}]" for r in relations]),
                        "score": 0.7,
                    })
                return RouterResult(Strategy.WIKI, results, 0.95)

        if self._is_graph_query(q):
            from graph.epistemic import EpistemicGraph
            graph = EpistemicGraph(layer=self.layer)
            # Ищем узлы по тегам связанных с запросом
            for tag in self._graph_keywords:
                if tag in q:
                    nodes = await graph.query_by_tag(self.user_id, tag, limit=5)
                    if nodes:
                        context = [{"title": n.content, "type": n.node_type, "tags": n.tags} for n in nodes]
                        return RouterResult(Strategy.GRAPH, context, 0.85)
            # Fallback: ищем по типу
            for node_type in ["decision_log", "error_analysis", "fact"]:
                if node_type.replace("_", " ") in q:
                    nodes = await graph.query_by_type(self.user_id, node_type, limit=5)
                    if nodes:
                        context = [{"title": n.content, "type": n.node_type, "tags": n.tags} for n in nodes]
                        return RouterResult(Strategy.GRAPH, context, 0.8)

        results = await self._rag.search_rrf(query, self.user_id, limit=3)
        if results:
            return RouterResult(Strategy.SEMANTIC, results, 0.8)

        return RouterResult(Strategy.SEMANTIC, [], 0.0)

    def _is_recent_query(self, query: str) -> bool:
        return len(query) < 60 and any(kw in query for kw in self._recent_keywords)

    def _is_wiki_query(self, query: str) -> bool:
        return any(kw in query for kw in self._wiki_keywords)

    def _is_graph_query(self, query: str) -> bool:
        return any(kw in query for kw in self._graph_keywords)
