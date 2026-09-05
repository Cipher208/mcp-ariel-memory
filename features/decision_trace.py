"""S13 semantica decision read-поверхность: trace_decision_chain.

По узлу-действию (epi_nodes) восстанавливает causal-цепочку action → outcome →
… — BFS вперёд по рёбрам epi_edges с relation из CAUSAL_RELATIONS (то, что
реально пишет graph/epistemic.py::record_causal — E17a/B1.7:
{"caused", "led_to", "prevented"}; «blocked» из ранних черновиков S13 не
существует в писателе). Read-only, no LLM.

Глубина ограничена `depth` (default 5), циклы обрываются visited-множеством.
Scope: узлы фильтруются по (layer, user_id) — чужие цепочки не видны.
"""

from __future__ import annotations

from typing import Any

from graph.epistemic import CAUSAL_RELATIONS


async def trace_decision_chain(node_id: int, user_id: str, depth: int = 5, *, layer: str = "user") -> dict[str, Any]:
    """BFS по causal-рёбрам от узла: {'root': {...} | None, 'chain': [...]}.

    chain — в порядке обхода BFS: {node_id, content, node_type, relation,
    strength, depth}, где relation/strength — ребро, которым узел достигнут,
    depth — расстояние от корня (1-based). root — тот же формат с
    relation/strength=None, depth=0. Несуществующий node_id (или узел другого
    user_id/layer) → {'root': None, 'chain': []}.
    """
    from shared.connection import connection_manager
    from shared.constants import DB_NAME

    conn = await connection_manager.get(DB_NAME)
    root_row = await (
        await conn.execute(
            "SELECT node_id, content, node_type FROM epi_nodes WHERE node_id=? AND layer=? AND user_id=?",
            (int(node_id), layer, user_id),
        )
    ).fetchone()
    if root_row is None:
        return {"root": None, "chain": []}

    root = {
        "node_id": int(root_row["node_id"]),
        "content": str(root_row["content"]),
        "node_type": str(root_row["node_type"]),
        "relation": None,
        "strength": None,
        "depth": 0,
    }

    chain: list[dict[str, Any]] = []
    visited = {int(node_id)}
    frontier = [int(node_id)]
    causal = sorted(CAUSAL_RELATIONS)
    for level in range(1, max(0, depth) + 1):
        if not frontier:
            break
        placeholders = ",".join("?" * len(frontier))
        causal_ph = ",".join("?" * len(causal))
        rows = await (
            await conn.execute(
                f"""SELECT e.target_id, e.relation, e.weight, n.content, n.node_type
                    FROM epi_edges e JOIN epi_nodes n ON n.node_id = e.target_id
                    WHERE e.source_id IN ({placeholders}) AND e.relation IN ({causal_ph})
                      AND n.layer = ? AND n.user_id = ?""",
                (*frontier, *causal, layer, user_id),
            )
        ).fetchall()
        frontier = []
        for r in rows:
            target_id = int(r["target_id"])
            if target_id in visited:
                continue
            visited.add(target_id)
            chain.append(
                {
                    "node_id": target_id,
                    "content": str(r["content"]),
                    "node_type": str(r["node_type"]),
                    "relation": str(r["relation"]),
                    "strength": float(r["weight"]),
                    "depth": level,
                }
            )
            frontier.append(target_id)
    return {"root": root, "chain": chain}
