"""S13 file↔DB reconciliation: wiki .md-файлы vs wiki_index.

WikiManager пишет пару (файл, строка wiki_index); расхождение появляется при
ручных правках/удалениях. reconcile() — read-only аудит:
  (a) orphan md — файл есть, индекс-строки нет (ручное создание, упавший save);
  (b) stale index — индекс-строка есть, файла нет (ручное удаление).

# ponytail: hash-мисматч (файл правлен руками после индексации) не проверяем —
# базы хэшей несогласованы: add() хэширует raw content, update() — весь
# отрендеренный .md (wiki/manager.py), дешёвого однозначного сравнения нет.
# Upgrade path: единый hash-базис в менеджере → сравнение content_hash здесь.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

# Авто-генераты, которые пишутся на диск без индексации (wiki/manager.py
# _write_moc, wiki/lint INDEX-stub) — не orphans.
_AUTO_GENERATED = {"INDEX.md"}


async def reconcile(user_id: str = "default", layer: str = "user") -> dict[str, Any]:
    """Сверка wiki-файлов и wiki_index: {'orphans': [paths], 'stale': [paths], 'checked': N}.

    checked = число сверённых пар (md-файлы + индекс-строки слоя). user_id —
    совместимость сигнатуры memory_audit: wiki_index не юзер-скоуплен, аудит
    идёт по (layer, file_path). Каталог wiki берётся из connection_manager
    (тот же data dir, что у WikiManager — wiki/manager.py docstring).
    """
    from shared.connection import connection_manager
    from shared.constants import DB_NAME

    base_dir = Path(str(connection_manager.base_dir)) / "wiki" / layer
    conn = await connection_manager.get(DB_NAME)
    db_paths = {str(r["file_path"]) for r in (await (await conn.execute("SELECT file_path FROM wiki_index WHERE layer=?", (layer,))).fetchall())}

    def _scan() -> tuple[list[Path], list[str]]:
        files: list[Path] = []
        if base_dir.exists():
            for type_dir in sorted(base_dir.iterdir()):
                if not type_dir.is_dir() or type_dir.name == "_retired":
                    continue
                for f in sorted(type_dir.glob("*.md")):
                    if f.name in _AUTO_GENERATED or f.name.startswith("MOC_"):
                        continue
                    files.append(f)
        stale = sorted(p for p in db_paths if not Path(p).exists())  # ASYNC240: pathlib в потоке
        return files, stale

    md_files, stale = await asyncio.to_thread(_scan)
    orphans = [str(f) for f in md_files if str(f) not in db_paths]
    return {"orphans": orphans, "stale": stale, "checked": len(md_files) + len(db_paths)}
