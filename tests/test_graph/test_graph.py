"""Tests for graph/ module — async."""
import sys
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_epistemic_add_query():
    from graph.epistemic import EpistemicGraph
    async def t():
        g = EpistemicGraph(layer="test_graph")
        n = await g.add_node("t", "Likes Python", "fact", ["fact_about_user"], 0.9)
        assert n > 0
        nodes = await g.query_by_tag("t", "fact_about_user")
        assert len(nodes) >= 1
    asyncio.run(t())


def test_epistemic_neighbors():
    from graph.epistemic import EpistemicGraph
    async def t():
        g = EpistemicGraph(layer="test_graph")
        n1 = await g.add_node("t", "A", "fact")
        n2 = await g.add_node("t", "B", "fact")
        await g.add_edge(n1, n2, "related")
        neighbors = await g.get_neighbors(n1)
        assert len(neighbors) >= 1
    asyncio.run(t())


def test_epistemic_find_path():
    from graph.epistemic import EpistemicGraph
    async def t():
        g = EpistemicGraph(layer="test_graph")
        n1 = await g.add_node("t", "Start", "fact")
        n2 = await g.add_node("t", "End", "fact")
        await g.add_edge(n1, n2, "leads_to")
        path = await g.find_path(n1, n2)
        assert len(path) >= 1
    asyncio.run(t())


def test_temporal_timeline():
    from graph.temporal import TemporalGraph
    async def t():
        tg = TemporalGraph()
        e1 = await tg.add_event("t", "msg", "hello")
        e2 = await tg.add_event("t", "resp", "hi")
        await tg.link_events(e1, e2, "follows")
        timeline = await tg.get_timeline("t")
        assert len(timeline) >= 2
    asyncio.run(t())
