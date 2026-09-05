"""S13 file↔DB reconciliation: orphan md / stale index / чистый кейс."""

import time

import pytest

from shared.connection import connection_manager
from shared.constants import DB_NAME


@pytest.fixture
async def recon_db(tmp_path, monkeypatch):
    monkeypatch.setattr(connection_manager, "base_dir", tmp_path)  # патчим base_dir, не подменяем объект
    connection_manager._conns.clear()  # cached conns pin the old tmp dir
    from shared.migrations import migration_manager
    from wiki.index import WikiIndex

    await migration_manager.migrate()  # полная схема (audit_content читает core_memory и др.)
    await WikiIndex(connection_manager, "user").init_db()
    yield tmp_path
    connection_manager._conns.clear()


async def _index_row(file_path: str, title: str = "Ghost") -> None:
    conn = await connection_manager.get(DB_NAME)
    now = time.time()
    await conn.execute(
        "INSERT INTO wiki_index (layer, wiki_type, title, file_path, content, created_at, updated_at) VALUES ('user', 'concept', ?, ?, '', ?, ?)",
        (title, file_path, now, now),
    )
    await conn.commit()


async def test_orphan_file_without_index_row(recon_db):
    prefs = recon_db / "wiki" / "user" / "preferences"
    prefs.mkdir(parents=True)
    (prefs / "orphan.md").write_text("---\ntitle: Orphan\n---\nhand-made file\n", encoding="utf-8")
    (prefs / "MOC_preferences.md").write_text("# MOC\n", encoding="utf-8")  # авто-генерат — не orphan
    (prefs / "INDEX.md").write_text("# INDEX\n", encoding="utf-8")  # авто-генерат — не orphan

    from features.wiki_reconciliation import reconcile

    res = await reconcile("default")
    assert res["orphans"] == [str(prefs / "orphan.md")]
    assert res["stale"] == []
    assert res["checked"] == 1  # 1 реальный md-файл + 0 индекс-строк


async def test_stale_index_row_without_file(recon_db):
    await _index_row("/nonexistent/ghost.md")

    from features.wiki_reconciliation import reconcile

    res = await reconcile("default")
    assert res["orphans"] == []
    assert res["stale"] == ["/nonexistent/ghost.md"]
    assert res["checked"] == 1  # 0 файлов + 1 индекс-строка


async def test_clean_wiki_returns_empty_lists(recon_db):
    from features.wiki_reconciliation import reconcile
    from wiki.manager import WikiManager

    wm = WikiManager(layer="user", base_dir=str(recon_db / "wiki" / "user"), cm=connection_manager)
    path = await wm.add("preferences", "Coffee", "prefers coffee over tea")
    res = await reconcile("default")
    assert res["orphans"] == [], "файл, записанный WikiManager, проиндексирован"
    assert res["stale"] == []
    assert res["checked"] == 2  # 1 md-файл + 1 индекс-строка

    # ретир страницы убирает файл И строку — рассинхрона нет
    await wm.retire(path, reason="test")
    res2 = await reconcile("default")
    assert res2["orphans"] == [] and res2["stale"] == []


async def test_mixed_case_reports_both_sides(recon_db):
    prefs = recon_db / "wiki" / "user" / "diary"
    prefs.mkdir(parents=True)
    (prefs / "orphan.md").write_text("x", encoding="utf-8")
    await _index_row("/nonexistent/ghost.md", title="Ghost")

    from features.wiki_reconciliation import reconcile

    res = await reconcile("default")
    assert res["orphans"] == [str(prefs / "orphan.md")]
    assert res["stale"] == ["/nonexistent/ghost.md"]
    assert res["checked"] == 2  # 1 файл + 1 индекс-строка


async def test_audit_content_includes_reconciliation_check(recon_db):
    """WIRE: reconcile вызывается из audit_content как ещё один чек."""
    (recon_db / "wiki" / "user" / "preferences").mkdir(parents=True)
    (recon_db / "wiki" / "user" / "preferences" / "orphan.md").write_text("x", encoding="utf-8")

    from features.diagnostics import audit_content

    checks = {c["type"]: c for c in await audit_content("default")}
    rec = checks.get("wiki_reconciliation")
    assert rec is not None and rec["severity"] == "warn"
    assert {"orphan": str(recon_db / "wiki" / "user" / "preferences" / "orphan.md")} in rec["items"]
