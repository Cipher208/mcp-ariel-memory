"""
Retrieval Router - routes queries to the right memory strategy
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

    def route(self, query: str, recent_context: List[Dict] = None) -> RouterResult:
        q = query.lower()

        if self._is_recent_query(q) and recent_context:
            return RouterResult(Strategy.L1_BUFFER, recent_context, 0.9)

        if self._is_wiki_query(q):
            results = self._rag.search_rrf(query, self.user_id, limit=3)
            if results:
                page_id = results[0]["id"]
                relations = self._rag.get_relations(page_id, depth=1)
                if relations:
                    results.append({
                        "title": "Relations",
                        "content": "\n".join([f"- {r['title']} [{r['relation']}]" for r in relations]),
                        "score": 0.7
                    })
                return RouterResult(Strategy.WIKI, results, 0.95)

        results = self._rag.search_rrf(query, self.user_id, limit=3)
        if results:
            return RouterResult(Strategy.SEMANTIC, results, 0.8)

        return RouterResult(Strategy.SEMANTIC, [], 0.0)

    def _is_recent_query(self, query: str) -> bool:
        return len(query) < 60 and any(kw in query for kw in self._recent_keywords)

    def _is_wiki_query(self, query: str) -> bool:
        return any(kw in query for kw in self._wiki_keywords)
