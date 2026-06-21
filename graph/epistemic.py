"""
Epistemic Graph - tags and relations between knowledge items
"""
import sqlite3
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


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
    def __init__(self, db_path: str = None, layer: str = "user"):
        self.db_path = db_path or str(Path.home() / ".mcp-ariel-memory" / "graph.db")
        self.layer = layer
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_conn()
        try:
            conn.executescript("""
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
            conn.commit()
        finally:
            conn.close()

    def add_node(self, user_id: str, content: str, node_type: str,
                 tags: List[str] = None, confidence: float = 0.5) -> int:
        conn = self._get_conn()
        try:
            import json
            cursor = conn.execute(
                "INSERT INTO epi_nodes (user_id, content, node_type, tags, confidence, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, content, node_type, json.dumps(tags or []), confidence, time.time())
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def add_edge(self, source_id: int, target_id: int, relation: str, weight: float = 0.8):
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO epi_edges (source_id, target_id, relation, weight, created_at) VALUES (?, ?, ?, ?, ?)",
                (source_id, target_id, relation, weight, time.time())
            )
            conn.commit()
        finally:
            conn.close()

    def query_by_tag(self, user_id: str, tag: str, limit: int = 20) -> List[EpistemicNode]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM epi_nodes WHERE user_id=? AND tags LIKE ? ORDER BY confidence DESC LIMIT ?",
                (user_id, f'%"{tag}"%', limit)
            ).fetchall()
            return [self._row_to_node(r) for r in rows]
        finally:
            conn.close()

    def query_by_type(self, user_id: str, node_type: str, limit: int = 20) -> List[EpistemicNode]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM epi_nodes WHERE user_id=? AND node_type=? ORDER BY confidence DESC LIMIT ?",
                (user_id, node_type, limit)
            ).fetchall()
            return [self._row_to_node(r) for r in rows]
        finally:
            conn.close()

    def get_neighbors(self, node_id: int, depth: int = 1) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        try:
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
            rows = conn.execute(sql, (node_id, depth)).fetchall()
            import json
            return [
                {"id": r[0], "content": r[1], "type": r[2],
                 "tags": json.loads(r[3]) if r[3] else [], "relation": r[4], "weight": r[5]}
                for r in rows
            ]
        finally:
            conn.close()

    def find_path(self, source_id: int, target_id: int, max_depth: int = None) -> List[Dict[str, Any]]:
        """Найти путь между двумя узлами.
        max_depth по умолчанию берётся из config.graph.max_depth (default: 3).
        """
        if max_depth is None:
            try:
                from config import config
                max_depth = config.get("graph", "max_depth") or 3
            except Exception:
                max_depth = 3
        conn = self._get_conn()
        try:
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
            rows = conn.execute(sql, (source_id, max_depth, target_id)).fetchall()
            return [{"target": r[0], "relation": r[1], "weight": r[2], "depth": r[3]} for r in rows]
        finally:
            conn.close()

    def count_nodes(self, user_id: str = None) -> int:
        conn = self._get_conn()
        try:
            if user_id:
                row = conn.execute("SELECT COUNT(*) FROM epi_nodes WHERE user_id=?", (user_id,)).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) FROM epi_nodes").fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    def _row_to_node(self, row) -> EpistemicNode:
        import json
        return EpistemicNode(
            node_id=row["node_id"], user_id=row["user_id"], content=row["content"],
            node_type=row["node_type"], tags=json.loads(row["tags"]) if row["tags"] else [],
            confidence=row["confidence"], created_at=row["created_at"]
        )
