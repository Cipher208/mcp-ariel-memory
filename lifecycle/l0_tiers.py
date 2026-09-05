"""S6 — три тира l0_journal: горячий / тёплый / холодный (+ CLACK-экспорт).

- горячий 0–30д: нетронут;
- тёплый 30–180д (обработанные): text → extractive-превью (первые ~2
  предложения), полный текст уезжает в text_z BLOB (zlib, lossless);
- холодный >180д (обработанные): перенос в l0_cold_archive с PLAINTEXT
  полным текстом (LLM читает напрямую, без распаковки), строка удаляется
  из l0_journal; месяц записи выгружается в <data_dir>/l0_cold/<month>.clack.jsonl
  (CLACK: одна строка = один JSON-блок = мета decision-vector + plaintext).

received-статус НИКОГДА не архивируется и не режется. Гейт: l0.tiers_enabled.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import re
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import config
from shared.connection import connection_manager
from shared.constants import DB_NAME

# Обработанные статусы (S1): received → один из этих. received не тирится никогда.
_PROCESSED = ("promoted_l4", "saved_l3", "gated_out")
_PLACEHOLDERS = ",".join("?" * len(_PROCESSED))

_PREVIEW_SENTENCES = 2
_PREVIEW_CAP = 400
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…。])\s+")


def _preview(text: str) -> str:
    """Extractive-превью: первые ~2 предложения (жёсткий cap по символам)."""
    parts = _SENTENCE_SPLIT.split(text.strip(), maxsplit=_PREVIEW_SENTENCES)
    return " ".join(parts[:_PREVIEW_SENTENCES]).strip()[:_PREVIEW_CAP]


async def _ensure_schema(cm: Any) -> None:
    """Idempotent schema setup — зеркало миграции g22 для живых БД до неё."""
    conn = await cm.get(DB_NAME)
    await conn.execute(
        """CREATE TABLE IF NOT EXISTS l0_cold_archive (
            id INTEGER PRIMARY KEY,
            ts REAL NOT NULL,
            event TEXT NOT NULL,
            raw_type TEXT NOT NULL DEFAULT 'plain',
            layer TEXT NOT NULL DEFAULT 'user',
            user_id TEXT NOT NULL DEFAULT 'default',
            decisions TEXT NOT NULL DEFAULT '[]',
            archived_at REAL NOT NULL,
            text TEXT NOT NULL
        )"""
    )
    for ddl in (
        "ALTER TABLE l0_journal ADD COLUMN tier TEXT",
        "ALTER TABLE l0_journal ADD COLUMN text_z BLOB",
    ):
        with contextlib.suppress(Exception):  # колонка уже есть
            await conn.execute(ddl)
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_cold_ts ON l0_cold_archive(ts)")


def _parse_decisions(raw: Any) -> list[dict[str, Any]]:
    with contextlib.suppress(Exception):
        parsed = json.loads(raw) if raw else []
        return parsed if isinstance(parsed, list) else []
    return []


async def tier_l0(
    *,
    now: float | None = None,
    cm: Any | None = None,
) -> dict[str, Any]:
    """Ночной проход по тирам. Возвращает счётчики для отчёта backup_cron.

    received не трогается; обработанные 30–180д → warm (превью + zlib),
    обработанные >180д → cold archive (plaintext) + удаление из журнала.
    """
    if not config.get("l0", "tiers_enabled", default=True):
        return {"warm": 0, "cold": 0, "skipped": "disabled"}
    cm = cm or connection_manager
    conn = await cm.get(DB_NAME)
    await _ensure_schema(cm)
    ts_now = now if now is not None else time.time()
    warm_cutoff = ts_now - 30 * 86400
    cold_cutoff = ts_now - 180 * 86400
    archived_at = time.time()

    # --- холодный тир: >180д, обработанные → l0_cold_archive + удаление ---
    cold_rows = list(
        await (
            await conn.execute(
                f"""SELECT id, ts, event, raw_type, layer, user_id, decisions, text, text_z
                    FROM l0_journal
                    WHERE status IN ({_PLACEHOLDERS}) AND ts <= ?
                    ORDER BY id""",
                (*_PROCESSED, cold_cutoff),
            )
        ).fetchall()
    )
    months: set[str] = set()
    for rid, ts, event, raw_type, layer, user_id, decisions, text, text_z in cold_rows:
        full = text
        if text_z:
            with contextlib.suppress(Exception):
                full = zlib.decompress(bytes(text_z)).decode("utf-8")
        # id явно = PK архива: повторный прогон идемпотентен (OR IGNORE), дублей нет
        await conn.execute(
            """INSERT OR IGNORE INTO l0_cold_archive
               (id, ts, event, raw_type, layer, user_id, decisions, archived_at, text)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (rid, ts, event, raw_type, layer, user_id, decisions if decisions is not None else "[]", archived_at, full),
        )
        await conn.execute("DELETE FROM l0_journal WHERE id = ?", (rid,))
        months.add(time.strftime("%Y-%m", time.gmtime(ts)))

    # --- тёплый тир: 30–180д, обработанные, ещё не тёплые → превью + zlib ---
    warm_rows = list(
        await (
            await conn.execute(
                f"""SELECT id, text FROM l0_journal
                    WHERE status IN ({_PLACEHOLDERS}) AND tier IS NULL AND ts <= ? AND ts > ?
                    ORDER BY id""",
                (*_PROCESSED, warm_cutoff, cold_cutoff),
            )
        ).fetchall()
    )
    await conn.executemany(
        "UPDATE l0_journal SET tier = 'warm', text = ?, text_z = ? WHERE id = ?",
        [(_preview(text), zlib.compress(text.encode("utf-8")), rid) for rid, text in warm_rows],
    )
    await conn.commit()

    exported = [await export_clack(m, cm=cm) for m in sorted(months)]
    return {"warm": len(warm_rows), "cold": len(cold_rows), "exported": exported}


async def read_cold(since_days: float, *, cm: Any | None = None) -> list[dict[str, Any]]:
    """Мета-блоки (decision vector) из холодного архива за окно since_days.

    Потребитель решает по мете {id, ts, event, raw_type, layer, user_id,
    decisions, archived_at, brief} без вызовов; text — полный plaintext.
    """
    cm = cm or connection_manager
    conn = await cm.get(DB_NAME)
    cutoff = time.time() - since_days * 86400
    rows = list(
        await (
            await conn.execute(
                """SELECT id, ts, event, raw_type, layer, user_id, decisions, archived_at, text
                   FROM l0_cold_archive WHERE archived_at >= ? ORDER BY ts DESC, id DESC LIMIT 500""",
                (cutoff,),
            )
        ).fetchall()
    )
    return [
        {
            "id": rid,
            "ts": ts,
            "event": event,
            "raw_type": raw_type,
            "layer": layer,
            "user_id": user_id,
            "decisions": _parse_decisions(decisions),
            "archived_at": archived_at,
            "brief": text[:200],
            "text": text,
        }
        for rid, ts, event, raw_type, layer, user_id, decisions, archived_at, text in rows
    ]


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


async def export_clack(month: str, *, cm: Any | None = None) -> str:
    """CLACK-файл месяца: data_dir/l0_cold/<month>.clack.jsonl.

    Одна строка = один JSON-блок (полная мета + plaintext text) — формат
    читается любой LLM как есть, без распаковки; файл перезаписывается
    целиком (идемпотентно, полная выгрузка месяца из архива).
    """
    cm = cm or connection_manager
    y, m = (int(p) for p in month.split("-"))
    start = datetime(y, m, 1, tzinfo=timezone.utc).timestamp()  # ValueError на кривом месяце
    end = datetime(y + 1, 1, 1, tzinfo=timezone.utc).timestamp() if m == 12 else datetime(y, m + 1, 1, tzinfo=timezone.utc).timestamp()
    conn = await cm.get(DB_NAME)
    rows = list(
        await (
            await conn.execute(
                """SELECT id, ts, event, raw_type, layer, user_id, decisions, archived_at, text
                   FROM l0_cold_archive WHERE ts >= ? AND ts < ? ORDER BY ts, id""",
                (start, end),
            )
        ).fetchall()
    )
    lines = [
        json.dumps(
            {
                "id": rid,
                "ts": ts,
                "event": event,
                "raw_type": raw_type,
                "layer": layer,
                "user_id": user_id,
                "decisions": _parse_decisions(decisions),
                "archived_at": archived_at,
                "text": text,
            },
            ensure_ascii=False,
        )
        for rid, ts, event, raw_type, layer, user_id, decisions, archived_at, text in rows
    ]
    path = Path(cm.base_dir) / "l0_cold" / f"{month}.clack.jsonl"
    content = "\n".join(lines) + ("\n" if lines else "")
    await asyncio.to_thread(_write_file, path, content)
    return str(path)
