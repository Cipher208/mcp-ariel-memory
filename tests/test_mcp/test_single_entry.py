"""F-T9 single-entry: инвариант «нет обходных записей в граф».

Контракт (docs/compose/plans/2026-09-05-phase-f-pipeline.md Task 9):
- memory_remember не dual-writes граф (L4-only, граф наполняет дистиллятор/минеры);
- memory_graph_add требует provenance (source) и confidence;
- греп-инвариант: add_node вне разрешённых файлов отсутствует.
"""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from shared.connection import AsyncConnectionManager
from shared.migrations import MigrationManager

REPO_ROOT = Path(__file__).resolve().parents[2]

# Разрешённые прямые add_node (grep-инвариант F-T9 Step 3):
_ADD_NODE_ALLOWED = {
    "graph/epistemic.py",  # определение EpistemicGraph.add_node
    "lifecycle/graph_miners.py",  # минеры — штатный наполнитель
    "lifecycle/wiki_communities.py",  # networkx-граф сообществ (не EpistemicGraph)
    "mcp_server/tools/graph.py",  # валидированный вход (provenance+confidence)
}


def _files_with_add_node() -> list[str]:
    """Все файлы .py с вызовом add_node (AST: Call на attr add_node)."""
    hits: list[str] = []
    for path in sorted(REPO_ROOT.rglob("*.py")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel.startswith(("tests/", ".venv", "__pycache__", "build")) or "__pycache__" in rel:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_node":
                hits.append(rel)
                break
    return hits


def test_grep_invariant_no_bypass_add_node():
    """add_node допустим только в разрешённых файлах (см. _ADD_NODE_ALLOWED)."""
    violations = set(_files_with_add_node()) - _ADD_NODE_ALLOWED
    assert not violations, f"Обходные записи в граф: {sorted(violations)}"


@pytest.fixture
async def app(tmp_path):
    """Реальный AppContext с временной БД (паттерн test_tools_e2e.app)."""
    cm = AsyncConnectionManager(base_dir=str(tmp_path))
    mm = MigrationManager(cm=cm)
    await mm.migrate()

    from core import MemoryManager as MM
    from features.rate_limiting import RateLimiter
    from graph.epistemic import EpistemicGraph
    from hooks.agent_hooks import AgentHooks
    from hooks.user_hooks import UserHooks
    from lifecycle.emotion import EmotionTrigger, EmotionEngine, load_emotion_config
    from shared.cache import MemoryCache
    from wiki import WikiManager

    class App:
        pass

    app = App()
    app.mm = MM(cm=cm)
    app.cache = MemoryCache()
    app.user_wiki = WikiManager(layer="user", base_dir=str(tmp_path / "wiki_u"), cm=cm)
    app.agent_wiki = WikiManager(layer="agent", base_dir=str(tmp_path / "wiki_a"), cm=cm)
    app.user_graph = EpistemicGraph(layer="user", cm=cm)
    app.agent_graph = EpistemicGraph(layer="agent", cm=cm)

    emo_cfg = load_emotion_config()
    app.emotion_engine = EmotionEngine(config=emo_cfg)
    app.emotion_trigger = EmotionTrigger(app.emotion_engine)
    app.rate_limiter = RateLimiter()
    app.user_hooks = UserHooks()
    app.agent_hooks = AgentHooks()
    app.cm = cm  # тесты читают БД через тот же manager, что и фикстура
    return app


def _make_ctx(app):
    ctx = MagicMock()
    ctx.request_context = MagicMock()
    ctx.request_context.lifespan_context = app
    return ctx


@pytest.mark.asyncio
async def test_remember_does_not_write_graph(app):
    """memory_remember пишет только L4; spy на graph.add_node остаётся нетронутым."""
    from mcp_server.tools.memory import memory_remember

    ctx = _make_ctx(app)
    spy = AsyncMock(return_value=42)
    app.user_graph.add_node = spy

    result = await memory_remember(layer="user", user_id="se", key="k", value="value", ctx=ctx)

    assert result["status"] == "ok"
    spy.assert_not_called(), "L4-запись не дублирует контент в граф (F-T9)"
    assert result["graph_node_id"] is None


@pytest.mark.asyncio
async def test_remember_agent_layer_does_not_write_graph(app):
    """То же для agent-слоя (там dual-write был через asyncio.gather)."""
    from mcp_server.tools.memory import memory_remember

    ctx = _make_ctx(app)
    spy = AsyncMock(return_value=42)
    app.agent_graph.add_node = spy

    result = await memory_remember(layer="agent", user_id="sa", key="e_dec", value="Use async", importance=0.8, ctx=ctx)

    assert result["status"] == "ok"
    spy.assert_not_called()
    assert result["graph_node_id"] is None


@pytest.mark.asyncio
async def test_graph_add_requires_provenance(app):
    """memory_graph_add без source → ValueError (провенанс обязателен)."""
    from mcp_server.tools.graph import memory_graph_add

    ctx = _make_ctx(app)
    with pytest.raises(ValueError, match="provenance"):
        await memory_graph_add(layer="user", user_id="gp", content="x", node_type="fact", ctx=ctx)


@pytest.mark.asyncio
async def test_graph_add_requires_confidence(app):
    """memory_graph_add с source, но без confidence → ValueError."""
    from mcp_server.tools.graph import memory_graph_add

    ctx = _make_ctx(app)
    with pytest.raises(ValueError, match="confidence"):
        await memory_graph_add(layer="user", user_id="gp", content="x", node_type="fact", source="agent", ctx=ctx)


@pytest.mark.asyncio
async def test_graph_add_with_provenance_writes_tag(app):
    """Валидированный вход проходит и материализует provenance-тег."""
    from mcp_server.tools.graph import memory_graph_add

    ctx = _make_ctx(app)
    result = await memory_graph_add(layer="user", user_id="gp", content="x", node_type="fact", source="test", confidence=0.9, ctx=ctx)
    assert result["node_id"], f"node создан: {result}"

    conn = await app.cm.get("memory.db")
    row = await (await conn.execute("SELECT tags, confidence FROM epi_nodes WHERE node_id=?", (result["node_id"],))).fetchone()
    assert "provenance:test" in (row["tags"] or "")
    assert row["confidence"] == pytest.approx(0.9)
