"""S10/S12: 6-й RRF-источник (entities) + минер #7 по f:-парам.

- entities-источник: токены запроса через rag/synonyms канонизируются в классы;
  epi_nodes, чей content содержит член класса, добавляются КАНДИДАТАМИ
  (RRF-фьюжен добавляет, не заменяет; include_* контракт не ломается).
- f:-пары co-retrieval: тесты минера живут в tests/test_lifecycle/test_graph_miners.py
  (rag_pages.path → wiki_page-узел); здесь — сквозной check, что entity-хиты
  журналируются в recall_co_pairs как g:-ссылки (единое id-пространство графа).
"""

from typing import Any

import pytest

from shared.connection import connection_manager
from shared.constants import DB_NAME
from shared.migrations import MigrationManager


@pytest.fixture
async def db(tmp_path):
    original = connection_manager.base_dir
    connection_manager.base_dir = tmp_path
    connection_manager._conns.clear()
    await MigrationManager(cm=connection_manager).migrate()
    yield connection_manager
    connection_manager._conns.clear()
    connection_manager.base_dir = original


async def _node(content: str, user_id: str = "gu") -> int:
    conn = await connection_manager.get(DB_NAME)
    cur = await conn.execute(
        "INSERT INTO epi_nodes (layer, user_id, content, node_type, tags, confidence, created_at)"
        " VALUES ('user', ?, ?, 'fact', '[]', 0.5, 1700000000.0)",
        (user_id, content),
    )
    await conn.commit()
    return int(cur.lastrowid or 0)


@pytest.mark.asyncio
async def test_entity_source_finds_synonym_match(db):
    """'postgres tuning' при синониме postgres/postgresql находит узел с 'postgresql' в content."""
    from rag.multi_source import MultiSourceRAG

    nid = await _node("настройка postgresql: tuning и вакуум")

    multi = MultiSourceRAG(rag=None, wiki=None, cm=connection_manager)
    res = await multi.search("postgres tuning", user_id="gu", limit=10)

    ids = [h["id"] for h in res]
    assert -nid - 3_000_000 in ids, f"entity-хит должен попасть в выдачу: {ids}"
    hit = next(h for h in res if h["id"] == -nid - 3_000_000)
    assert hit["source"] == "entities"


@pytest.mark.asyncio
async def test_entity_source_adds_candidates_does_not_replace(db):
    """Прямые хиты остаются сверху: entity-кандидат имеет фиксированный скор 0.45."""
    from rag.multi_source import MultiSourceRAG

    await _node("postgresql вакуум")

    class _Rag:
        async def search(self, query: str, **kw: Any) -> list[dict[str, Any]]:
            return [{"id": 7, "title": "t", "content": "postgres tuning напрямую", "score": 0.9, "source": "fts5"}]

    multi = MultiSourceRAG(rag=_Rag(), wiki=None, cm=connection_manager)
    res = await multi.search("postgres tuning", user_id="gu", limit=10)

    sources = [h["source"] for h in res]
    assert "fts5" in sources and "entities" in sources, f"фьюжен добавляет, не заменяет: {res}"
    assert res[0]["source"] == "fts5", "прямой хит (0.9) выше entity-кандидата (0.45)"


@pytest.mark.asyncio
async def test_entity_source_flag_off(db):
    """include_entities=False — контракт include_-флагов: источника нет в выдаче."""
    from rag.multi_source import MultiSourceRAG

    await _node("postgresql вакуум")

    multi = MultiSourceRAG(rag=None, wiki=None, cm=connection_manager)
    res = await multi.search("postgres tuning", user_id="gu", limit=10, include_entities=False)

    assert all(h.get("source") != "entities" for h in res), res


@pytest.mark.asyncio
async def test_entity_source_config_flag_off(db, monkeypatch):
    """config rag.entity_rrf=false — дефолт выключен (include_entities не передан)."""
    from config import config
    from rag.multi_source import MultiSourceRAG

    await _node("postgresql вакуум")
    monkeypatch.setattr(config, "_data", {**getattr(config, "_data", {}), "rag": {"entity_rrf": False}}, raising=False)

    multi = MultiSourceRAG(rag=None, wiki=None, cm=connection_manager)
    res = await multi.search("postgres tuning", user_id="gu", limit=10)

    assert all(h.get("source") != "entities" for h in res), res


@pytest.mark.asyncio
async def test_entity_hits_journal_as_graph_refs(db):
    """Entity-хиты живут в графовом id-пространстве → журнал co-retrieval пишет g:-ссылки."""
    from lifecycle.graph_miners import log_co_pairs
    from rag.multi_source import MultiSourceRAG

    await _node("postgresql вакуум")
    await _node("psql репликация tuning")  # второй член класса → ≥2 хита → пара

    multi = MultiSourceRAG(rag=None, wiki=None, cm=connection_manager)
    res = await multi.search("postgres tuning", user_id="gu", limit=10)
    assert len(res) >= 2, f"нужно ≥2 entity-хита для пары: {res}"

    written = await log_co_pairs(connection_manager, "postgres tuning", res)
    conn = await connection_manager.get(DB_NAME)
    rows = await (await conn.execute("SELECT node_a, node_b FROM recall_co_pairs")).fetchall()
    assert written == len(rows) > 0
    assert all(r["node_a"].startswith("g:") and r["node_b"].startswith("g:") for r in rows), rows


@pytest.mark.asyncio
async def test_entity_source_no_cm_and_no_vocab_is_noop():
    """Без cm или без словарных токенов источник пуст — дефолтное поведение не меняется."""
    from rag.multi_source import MultiSourceRAG

    assert await MultiSourceRAG(rag=None, wiki=None, cm=None)._from_entities("postgres tuning", "gu", 10, "hybrid", 1.0) == []
    assert await MultiSourceRAG(rag=None, wiki=None, cm=None).search("полностью словарный запрос без синонимов") == []
