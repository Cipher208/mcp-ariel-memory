"""Tests for graph/ module (epistemic + temporal)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_epistemic_add_query():
    from graph.epistemic import EpistemicGraph
    g = EpistemicGraph(layer="test_graph")
    n = g.add_node("t", "Likes Python", "fact", ["fact_about_user"], 0.9)
    assert n > 0
    nodes = g.query_by_tag("t", "fact_about_user")
    assert len(nodes) >= 1


def test_epistemic_neighbors():
    from graph.epistemic import EpistemicGraph
    g = EpistemicGraph(layer="test_graph")
    n1 = g.add_node("t", "A", "fact")
    n2 = g.add_node("t", "B", "fact")
    g.add_edge(n1, n2, "related")
    neighbors = g.get_neighbors(n1)
    assert len(neighbors) >= 1


def test_epistemic_find_path():
    from graph.epistemic import EpistemicGraph
    g = EpistemicGraph(layer="test_graph")
    n1 = g.add_node("t", "Start", "fact")
    n2 = g.add_node("t", "End", "fact")
    g.add_edge(n1, n2, "leads_to")
    path = g.find_path(n1, n2)
    assert len(path) >= 1


def test_temporal_timeline():
    from graph.temporal import TemporalGraph
    tg = TemporalGraph()
    e1 = tg.add_event("t", "msg", "hello")
    e2 = tg.add_event("t", "resp", "hi")
    tg.link_events(e1, e2, "follows")
    timeline = tg.get_timeline("t")
    assert len(timeline) >= 2
