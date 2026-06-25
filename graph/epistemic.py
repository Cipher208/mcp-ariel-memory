"""
Epistemic Graph - tags and relations between knowledge items
"""
import time
from typing import List, Dict, Any
from dataclasses import dataclass
from shared.connection import AsyncConnectionManager, connection_manager


@dataclass
class EpistemicNode:
    node_id: int
    user_id: str
    content: str
    node_type: str
    tags: List[str]
    confidence: float
    created_at: float


@dataclass
class EpistemicEdge:
    source_id: int
    target_id: int
    relation: str
    weight: float
    created_at: float


# User layer tags
USER_TAGS = {
    "fact_about_user": "Факт о пользователе",
    "user_decision": "Решение пользователя",
    "user_preference": "Предпочтение пользователя",
    "user_emotion": "Эмоция пользователя",
}

# Agent layer tags
AGENT_TAGS = {
    "learned_from": "Агент узнал из ошибки",
    "decided_because": "Агент принял решение",
    "evolved_to": "Личность изменилась",
    "felt_in_context": "Эмоция в контексте",
    "wiki_contains": "Вторая кора мозга",
    "error_pattern": "Паттерн ошибки",
    "correction_pattern": "Паттерн исправления",
    "personality_trait": "Черта личности",
}


class EpistemicGraph:
    def __init__(self, cm=None, layer: str = "user"):
        self._cm = cm or connection_manager
        self.layer = layer

    async def init_db(self):
        await self._cm.execute_script("memory.db", """
            CREATE TABLE IF NOT EXISTS epi_nodes (
                node_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                node_type TEXT NOT NULL,
                tags TEXT,
                confidence REAL DEFAULT 0.5,
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS epi_edges (
                source_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                relation TEXT NOT NULL,
                weight REAL DEFAULT 0.8,
                created_at REAL NOT NULL,
                PRIMARY KEY (source_id, target_id, relation)
            );
            CREATE INDEX IF NOT EXISTS idx_epi_user ON epi_nodes(user_id);
            CREATE INDEX IF NOT EXISTS idx_epi_type ON epi_nodes(node_type);
            CREATE INDEX IF NOT EXISTS idx_epi_tags ON epi_nodes(tags);
        """)

    async def add_node(self, user_id: str, content: str, node_type: str,
                       tags: List[str] = None, confidence: float = 0.5) -> int:
        import json
        conn = await self._cm.get("memory.db")
        cursor = await conn.execute(
            "INSERT INTO epi_nodes (user_id, content, node_type, tags, confidence, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, content, node_type, json.dumps(tags or []), confidence, time.time())
        )
        await conn.commit()
        return cursor.lastrowid

    async def add_edge(self, source_id: int, target_id: int, relation: str, weight: float = 0.8):
        conn = await self._cm.get("memory.db")
        await conn.execute(
            "INSERT OR REPLACE INTO epi_edges (source_id, target_id, relation, weight, created_at) VALUES (?, ?, ?, ?, ?)",
            (source_id, target_id, relation, weight, time.time())
        )
        await conn.commit()

    async def query_by_tag(self, user_id: str, tag: str, limit: int = 20) -> List[EpistemicNode]:
        conn = await self._cm.get("memory.db")
        cur = await conn.execute(
            "SELECT * FROM epi_nodes WHERE user_id=? AND tags LIKE ? ORDER BY confidence DESC LIMIT ?",
            (user_id, f'%"{tag}"%', limit)
        )
        rows = await cur.fetchall()
        return [self._row_to_node(r) for r in rows]

    async def query_by_type(self, user_id: str, node_type: str, limit: int = 20) -> List[EpistemicNode]:
        conn = await self._cm.get("memory.db")
        cur = await conn.execute(
            "SELECT * FROM epi_nodes WHERE user_id=? AND node_type=? ORDER BY confidence DESC LIMIT ?",
            (user_id, node_type, limit)
        )
        rows = await cur.fetchall()
        return [self._row_to_node(r) for r in rows]

    async def get_neighbors(self, node_id: int, depth: int = 1) -> List[Dict[str, Any]]:
        conn = await self._cm.get("memory.db")
        sql = """
        WITH RECURSIVE graph AS (
            SELECT e.source_id, e.target_id, e.relation, e.weight, 1 as d
            FROM epi_edges e WHERE e.source_id = ?
            UNION ALL
            SELECT e.source_id, e.target_id, e.relation, e.weight, g.d + 1
            FROM epi_edges e JOIN graph g ON e.source_id = g.target_id
            WHERE g.d < ?
        )
        SELECT n.node_id, n.content, n.node_type, n.tags, g.relation, g.weight
        FROM graph g JOIN epi_nodes n ON g.target_id = n.node_id
        """
        cur = await conn.execute(sql, (node_id, depth))
        rows = await cur.fetchall()
        import json
        return [
            {"id": r[0], "content": r[1], "type": r[2],
             "tags": json.loads(r[3]) if r[3] else [], "relation": r[4], "weight": r[5]}
            for r in rows
        ]

    async def find_path(self, source_id: int, target_id: int, max_depth: int = None) -> List[Dict[str, Any]]:
        if max_depth is None:
            try:
                from config import config
                max_depth = config.get("graph", "max_depth") or 3
            except Exception:
                max_depth = 3
        conn = await self._cm.get("memory.db")
        sql = """
        WITH RECURSIVE path AS (
            SELECT source_id, target_id, relation, weight, 1 as d, source_id || '->' || target_id as path_str
            FROM epi_edges WHERE source_id = ?
            UNION ALL
            SELECT e.source_id, e.target_id, e.relation, e.weight, p.d + 1, p.path_str || '->' || e.target_id
            FROM epi_edges e JOIN path p ON e.source_id = p.target_id
            WHERE p.d < ? AND e.target_id NOT LIKE '%' || p.path_str || '%'
        )
        SELECT target_id, relation, weight, d FROM path WHERE target_id = ?
        LIMIT 1
        """
        cur = await conn.execute(sql, (source_id, max_depth, target_id))
        rows = await cur.fetchall()
        return [{"target": r[0], "relation": r[1], "weight": r[2], "depth": r[3]} for r in rows]

    async def count_nodes(self, user_id: str = None) -> int:
        conn = await self._cm.get("memory.db")
        if user_id:
            cur = await conn.execute("SELECT COUNT(*) FROM epi_nodes WHERE user_id=?", (user_id,))
        else:
            cur = await conn.execute("SELECT COUNT(*) FROM epi_nodes")
        row = await cur.fetchone()
        return row[0] if row else 0

    def _row_to_node(self, row) -> EpistemicNode:
        import json
        return EpistemicNode(
            node_id=row["node_id"], user_id=row["user_id"], content=row["content"],
            node_type=row["node_type"], tags=json.loads(row["tags"]) if row["tags"] else [],
            confidence=row["confidence"], created_at=row["created_at"]
        )
