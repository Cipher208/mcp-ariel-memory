"""
Legacy MemoryMCPServer — backward compatibility.

This module is NOT used for MCP protocol.
Main MCP server: mcp_server.py (FastMCP, async, 37 tools).

Legacy server is needed for:
- Tests (test_backward_compat)
- Direct Python calls without MCP protocol
- Backward compatibility with old code

If writing new code — use mcp_server.py or import modules directly.
"""

import asyncio
from typing import Any

from core import memory_manager
from features import BackupManager, ImportExport, MemoryCompressor
from graph.epistemic import EpistemicGraph
from graph.temporal import TemporalGraph
from hooks import HookRegistry
from lifecycle.consolidation import ConsolidationEngine
from lifecycle.emotion_trigger import EmotionTrigger
from lifecycle.forgetting import ForgettingSystem
from rag.engine import RAGEngine
from shared import MemoryCache
from wiki.file_wiki import FileWiki


class MemoryMCPServer:
    def __init__(self):
        self.mm = memory_manager
        self.user_wiki = FileWiki(layer="user")
        self.agent_wiki = FileWiki(layer="agent")
        self.user_rag = RAGEngine(layer="user")
        self.agent_rag = RAGEngine(layer="agent")
        self.user_graph = EpistemicGraph(layer="user")
        self.agent_graph = EpistemicGraph(layer="agent")
        self.temporal = TemporalGraph()
        self.forgetting = ForgettingSystem()
        self.emotion_trigger = EmotionTrigger()
        self.consolidation = ConsolidationEngine()
        self.import_export = ImportExport()
        self.backup = BackupManager()
        self.compressor = MemoryCompressor()
        self.cache = MemoryCache()
        self.hooks = HookRegistry()

        self._tools = self._register_tools()

    def _register_tools(self) -> dict[str, Any]:
        return {
            # User Layer (10 tools)
            "memory.user.remember": self.user_remember,
            "memory.user.recall": self.user_recall,
            "memory.user.forget": self.user_forget,
            "memory.user.session.start": self.user_session_start,
            "memory.user.session.end": self.user_session_end,
            "memory.user.episode.save": self.user_episode_save,
            "memory.user.episode.recall": self.user_episode_recall,
            "memory.user.graph.add": self.user_graph_add,
            "memory.user.graph.query": self.user_graph_query,
            "memory.user.stats": self.user_stats,
            # Agent Layer (10 tools)
            "memory.agent.remember": self.agent_remember,
            "memory.agent.recall": self.agent_recall,
            "memory.agent.forget": self.agent_forget,
            "memory.agent.session.start": self.agent_session_start,
            "memory.agent.session.end": self.agent_session_end,
            "memory.agent.episode.save": self.agent_episode_save,
            "memory.agent.episode.recall": self.agent_episode_recall,
            "memory.agent.graph.add": self.agent_graph_add,
            "memory.agent.graph.query": self.agent_graph_query,
            "memory.agent.stats": self.agent_stats,
        }

    def call(self, tool_name: str, **kwargs) -> dict[str, Any]:
        """Legacy sync call — for backward compatibility.
        Wraps async methods via asyncio.run().
        """
        tool = self._tools.get(tool_name)
        if not tool:
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            result = tool(**kwargs)
            if asyncio.iscoroutine(result):
                result = asyncio.run(result)
            return result
        except Exception as e:
            return {"error": str(e)}

    # === User Layer Tools ===

    def user_remember(self, user_id: str = "default", key: str = "", value: str = "", importance: float = 0.5, **kw) -> dict:
        entry_id = self.mm.user_memory(user_id).remember(key, value, importance)
        return {"status": "ok", "entry_id": entry_id}

    def user_recall(self, user_id: str = "default", query: str = "", limit: int = 10, **kw) -> dict:
        results = self.mm.user_memory(user_id).recall(query, limit)
        return {"results": results, "count": len(results)}

    def user_forget(self, user_id: str = "default", key: str = "", **kw) -> dict:
        deleted = self.mm.user_memory(user_id).forget(key)
        return {"deleted": deleted}

    def user_session_start(self, user_id: str = "default", **kw) -> dict:
        session_id = self.mm.user_memory(user_id).l2.create_session(user_id)
        return {"session_id": session_id}

    def user_session_end(self, user_id: str = "default", session_id: str = "", summary: str = "", **kw) -> dict:
        self.mm.user_memory(user_id).l2.close_session(session_id, summary)
        return {"status": "ok"}

    def user_episode_save(self, user_id: str = "default", summary: str = "", weight: float = 0.5, tags: list = None, **kw) -> dict:
        episode_id = self.mm.user_memory(user_id).l3.save(user_id, summary, weight, tags)
        return {"episode_id": episode_id}

    def user_episode_recall(self, user_id: str = "default", tag: str = "", limit: int = 10, **kw) -> dict:
        if tag:
            episodes = self.mm.user_memory(user_id).l3.search_by_tag(user_id, tag, limit)
        else:
            episodes = self.mm.user_memory(user_id).l3.get_episodes(user_id, limit)
        return {"episodes": [{"id": e.episode_id, "summary": e.summary, "weight": e.emotional_weight} for e in episodes]}

    def user_graph_add(self, user_id: str = "default", content: str = "", node_type: str = "fact", tags: list = None, **kw) -> dict:
        node_id = self.user_graph.add_node(user_id, content, node_type, tags)
        return {"node_id": node_id}

    def user_graph_query(self, user_id: str = "default", tag: str = "", node_type: str = "", limit: int = 20, **kw) -> dict:
        if tag:
            nodes = self.user_graph.query_by_tag(user_id, tag, limit)
        elif node_type:
            nodes = self.user_graph.query_by_type(user_id, node_type, limit)
        else:
            nodes = []
        return {"nodes": [{"id": n.node_id, "content": n.content, "type": n.node_type, "tags": n.tags} for n in nodes]}

    def user_stats(self, user_id: str = "default", **kw) -> dict:
        mem = self.mm.user_memory(user_id)
        return {
            "l1_buffer": mem.l1.size(),
            "l2_sessions": mem.l2.count_sessions(user_id),
            "l3_episodes": len(mem.l3.get_episodes(user_id, 1000)),
            "l4_facts": mem.l4.count(user_id),
            "wiki_pages": self.user_wiki.count(user_id),
            "graph_nodes": self.user_graph.count_nodes(user_id),
        }

    # === Agent Layer Tools ===

    def agent_remember(self, user_id: str = "default", key: str = "", value: str = "", importance: float = 0.5, **kw) -> dict:
        entry_id = self.mm.agent_memory(user_id).remember(key, value, importance)
        return {"status": "ok", "entry_id": entry_id}

    def agent_recall(self, user_id: str = "default", query: str = "", limit: int = 10, **kw) -> dict:
        results = self.mm.agent_memory(user_id).recall(query, limit)
        return {"results": results, "count": len(results)}

    def agent_forget(self, user_id: str = "default", key: str = "", **kw) -> dict:
        deleted = self.mm.agent_memory(user_id).forget(key)
        return {"deleted": deleted}

    def agent_session_start(self, user_id: str = "default", **kw) -> dict:
        session_id = self.mm.agent_memory(user_id).l2.create_session(user_id)
        return {"session_id": session_id}

    def agent_session_end(self, user_id: str = "default", session_id: str = "", summary: str = "", **kw) -> dict:
        self.mm.agent_memory(user_id).l2.close_session(session_id, summary)
        return {"status": "ok"}

    def agent_episode_save(self, user_id: str = "default", summary: str = "", weight: float = 0.5, tags: list = None, **kw) -> dict:
        episode_id = self.mm.agent_memory(user_id).l3.save(user_id, summary, weight, tags)
        return {"episode_id": episode_id}

    def agent_episode_recall(self, user_id: str = "default", tag: str = "", limit: int = 10, **kw) -> dict:
        if tag:
            episodes = self.mm.agent_memory(user_id).l3.search_by_tag(user_id, tag, limit)
        else:
            episodes = self.mm.agent_memory(user_id).l3.get_episodes(user_id, limit)
        return {"episodes": [{"id": e.episode_id, "summary": e.summary, "weight": e.emotional_weight} for e in episodes]}

    def agent_graph_add(self, user_id: str = "default", content: str = "", node_type: str = "decision_log", tags: list = None, **kw) -> dict:
        node_id = self.agent_graph.add_node(user_id, content, node_type, tags)
        return {"node_id": node_id}

    def agent_graph_query(self, user_id: str = "default", tag: str = "", node_type: str = "", limit: int = 20, **kw) -> dict:
        if tag:
            nodes = self.agent_graph.query_by_tag(user_id, tag, limit)
        elif node_type:
            nodes = self.agent_graph.query_by_type(user_id, node_type, limit)
        else:
            nodes = []
        return {"nodes": [{"id": n.node_id, "content": n.content, "type": n.node_type, "tags": n.tags} for n in nodes]}

    def agent_stats(self, user_id: str = "default", **kw) -> dict:
        mem = self.mm.agent_memory(user_id)
        return {
            "l1_buffer": mem.l1.size(),
            "l2_sessions": mem.l2.count_sessions(user_id),
            "l3_episodes": len(mem.l3.get_episodes(user_id, 1000)),
            "l4_facts": mem.l4.count(user_id),
            "wiki_pages": self.agent_wiki.count(user_id),
            "graph_nodes": self.agent_graph.count_nodes(user_id),
        }

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def get_context(self, user_id: str = "default", layer: str = "user") -> str:
        return self.mm.get_layer(layer, user_id).get_context()


# Singleton
server = MemoryMCPServer()
