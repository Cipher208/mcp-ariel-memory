"""S13 trace_decision_chain: BFS по causal-цепочке из record_causal (E17a)."""

import pytest

from features.decision_trace import trace_decision_chain
from graph.epistemic import EpistemicGraph
from shared.connection import connection_manager


@pytest.fixture
async def graph_db(tmp_path, monkeypatch):
    monkeypatch.setattr(connection_manager, "base_dir", tmp_path)  # патчим base_dir, не подменяем объект
    connection_manager._conns.clear()  # cached conns pin the old tmp dir
    graph = EpistemicGraph(cm=connection_manager, layer="user")
    await graph.init_db()
    yield graph
    connection_manager._conns.clear()


async def test_trace_bfs_depth_two_and_deeper(graph_db):
    graph = graph_db
    # первая запись — через настоящий писатель record_causal
    action_id, outcome_id = await graph.record_causal(
        "u1", "migrated billing to PostgreSQL", "checkout latency dropped", relation="led_to", strength=0.9
    )
    assert outcome_id > 0
    # цепочку продолжаем поверх outcome-узла: outcome → next → next
    c_id = await graph.add_node("u1", "conversion rate up", "outcome", None, 0.8)
    d_id = await graph.add_node("u1", "revenue up", "outcome", None, 0.7)
    await graph.add_edge(outcome_id, c_id, "caused", 0.8)
    await graph.add_edge(c_id, d_id, "led_to", 0.7)

    res = await trace_decision_chain(action_id, "u1", depth=2)
    root = res["root"]
    assert root["node_id"] == action_id and root["node_type"] == "action" and root["depth"] == 0
    assert [c["node_id"] for c in res["chain"]] == [outcome_id, c_id], "depth 2: outcome на первом шаге + следующий"
    first = res["chain"][0]
    assert first["relation"] == "led_to" and abs(first["strength"] - 0.9) < 1e-9 and first["depth"] == 1
    assert res["chain"][1]["depth"] == 2

    deep = await trace_decision_chain(action_id, "u1")  # default depth 5 — вся цепочка
    assert [c["node_id"] for c in deep["chain"]] == [outcome_id, c_id, d_id]


async def test_trace_skips_non_causal_edges_and_cycles(graph_db):
    graph = graph_db
    n1 = await graph.add_node("u1", "deploy friday", "action", None, 0.9)
    n2 = await graph.add_node("u1", "incident", "outcome", None, 0.9)
    n3 = await graph.add_node("u1", "rollback", "action", None, 0.8)
    n4 = await graph.add_node("u1", "revenue up", "outcome", None, 0.7)
    await graph.add_edge(n1, n2, "led_to", 0.9)
    await graph.add_edge(n1, n4, "knows", 0.99)  # не causal — не входит в трейс
    await graph.add_edge(n2, n3, "caused", 0.8)
    await graph.add_edge(n3, n1, "caused", 0.5)  # цикл — обрывается visited

    res = await trace_decision_chain(n1, "u1")
    assert [c["node_id"] for c in res["chain"]] == [n2, n3]
    assert {c["relation"] for c in res["chain"]} <= {"led_to", "caused", "prevented"}


async def test_trace_scopes_by_user_and_missing_root(graph_db):
    graph = graph_db
    other_action, _ = await graph.record_causal("u2", "foreign deploy", "foreign outage", relation="led_to")
    res = await trace_decision_chain(other_action, "u1")
    assert res == {"root": None, "chain": []}, "чужой user_id невидим"

    own_action, own_outcome = await graph.record_causal("u1", "own deploy", "own outage", relation="caused", strength=0.6)
    res = await trace_decision_chain(own_action, "u1")
    assert [c["node_id"] for c in res["chain"]] == [own_outcome]
    assert res["chain"][0]["relation"] == "caused"

    assert await trace_decision_chain(999999, "u1") == {"root": None, "chain": []}
