"""
User Wiki — 7 types of user knowledge
Supports external folders for auto-sync
"""

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shared.connection import AsyncConnectionManager, connection_manager
from wiki.shared import (
    build_count_query,
    build_update_clause,
    find_by_source,
    format_search_result,
    get_enabled_types,
    get_external_dirs,
    parse_tags,
)


@dataclass
class WikiEntry:
    entry_id: int
    user_id: str
    wiki_type: str
    title: str
    content: str
    tags: list[str]
    importance: float
    created_at: float
    updated_at: float


ALL_WIKI_TYPES = ["diary", "relationships", "desires", "aspirations", "work_notes", "preferences", "retrospective"]


def _get_enabled_types() -> list[str]:
    """Get enabled wiki types from config."""
    return get_enabled_types("user", ALL_WIKI_TYPES)


def _get_external_dirs() -> list[str]:
    """Get external directories from config."""
    return get_external_dirs("user")


class UserWiki:
    def __init__(self, cm: AsyncConnectionManager = None):
        self._cm = cm or connection_manager

    async def init_db(self):
        await self._cm.execute_script(
            "memory.db",
            """
            CREATE TABLE IF NOT EXISTS user_wiki (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                wiki_type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT,
                importance REAL DEFAULT 0.5,
                source TEXT DEFAULT 'manual',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_uwiki_user ON user_wiki(user_id);
            CREATE INDEX IF NOT EXISTS idx_uwiki_type ON user_wiki(wiki_type);
            CREATE INDEX IF NOT EXISTS idx_uwiki_user_type ON user_wiki(user_id, wiki_type);
            CREATE INDEX IF NOT EXISTS idx_uwiki_source ON user_wiki(source);
            CREATE INDEX IF NOT EXISTS idx_uwiki_updated ON user_wiki(updated_at);
        """,
        )
        conn = await self._cm.get("memory.db")
        try:
            await conn.execute("ALTER TABLE user_wiki ADD COLUMN source TEXT DEFAULT 'manual'")
        except Exception:
            pass
        await conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS user_wiki_fts USING fts5(
                title, content, wiki_type,
                content=user_wiki,
                content_rowid=entry_id
            )
        """)
        await conn.commit()

    async def add(
        self,
        user_id: str,
        wiki_type: str,
        title: str,
        content: str,
        tags: list[str] = None,
        importance: float = 0.5,
        source: str = "manual",
    ) -> int:
        enabled = _get_enabled_types()
        if enabled and wiki_type not in enabled:
            raise ValueError(f"Wiki type '{wiki_type}' is disabled. Enabled: {enabled}")

        conn = await self._cm.get("memory.db")
        now = time.time()
        cur = await conn.execute(
            "INSERT INTO user_wiki (user_id, wiki_type, title, content, tags, importance, source, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, wiki_type, title, content, json.dumps(tags or []), importance, source, now, now),
        )
        entry_id = cur.lastrowid
        await conn.execute(
            "INSERT INTO user_wiki_fts(rowid, title, content, wiki_type) VALUES (?, ?, ?, ?)",
            (entry_id, title, content, wiki_type),
        )
        await conn.commit()
        return entry_id

    async def update(self, entry_id: int, title: str = None, content: str = None, tags: list[str] = None, importance: float = None):
        conn = await self._cm.get("memory.db")
        updates, params = build_update_clause({"title": title, "content": content, "tags": tags, "importance": importance})
        params.append(entry_id)
        await conn.execute(f"UPDATE user_wiki SET {', '.join(updates)} WHERE entry_id=?", params)
        await conn.commit()

    async def get(self, entry_id: int) -> WikiEntry | None:
        conn = await self._cm.get("memory.db")
        cur = await conn.execute("SELECT * FROM user_wiki WHERE entry_id=?", (entry_id,))
        row = await cur.fetchone()
        return self._row_to_entry(row) if row else None

    async def search(self, user_id: str, query: str, limit: int = 10) -> list[dict[str, Any]]:
        try:
            conn = await self._cm.get("memory.db")
            cur = await conn.execute(
                """SELECT uw.entry_id, uw.title, uw.content, uw.wiki_type, uw.tags, uw.importance, fts.rank
                   FROM user_wiki_fts fts JOIN user_wiki uw ON fts.rowid = uw.entry_id
                   WHERE user_wiki_fts MATCH ? AND uw.user_id = ?
                   ORDER BY fts.rank DESC LIMIT ?""",
                (query, user_id, limit),
            )
            rows = await cur.fetchall()
            return [format_search_result(r) for r in rows]
        except Exception:
            return []

    async def list_by_type(self, user_id: str, wiki_type: str, limit: int = 20) -> list[WikiEntry]:
        conn = await self._cm.get("memory.db")
        cur = await conn.execute(
            "SELECT * FROM user_wiki WHERE user_id=? AND wiki_type=? ORDER BY updated_at DESC LIMIT ?",
            (user_id, wiki_type, limit),
        )
        rows = await cur.fetchall()
        return [self._row_to_entry(r) for r in rows]

    async def list_all(self, user_id: str, limit: int = 50) -> list[WikiEntry]:
        conn = await self._cm.get("memory.db")
        cur = await conn.execute("SELECT * FROM user_wiki WHERE user_id=? ORDER BY updated_at DESC LIMIT ?", (user_id, limit))
        rows = await cur.fetchall()
        return [self._row_to_entry(r) for r in rows]

    async def delete(self, entry_id: int) -> bool:
        conn = await self._cm.get("memory.db")
        cur = await conn.execute("DELETE FROM user_wiki WHERE entry_id=?", (entry_id,))
        await conn.commit()
        return cur.rowcount > 0

    async def count(self, user_id: str = None, wiki_type: str = None) -> int:
        conn = await self._cm.get("memory.db")
        query, params = build_count_query("user_wiki", user_id, wiki_type)
        cur = await conn.execute(query, params)
        row = await cur.fetchone()
        return row[0] if row else 0

    def get_enabled_types(self) -> list[str]:
        return _get_enabled_types()

    def get_external_dirs(self) -> list[str]:
        return _get_external_dirs()

    async def sync_external(self, user_id: str) -> dict[str, int]:
        """Sync external .md files into wiki."""
        results = {"imported": 0, "skipped": 0, "errors": 0}
        for dir_path in _get_external_dirs():
            p = Path(dir_path)
            if not p.exists():
                continue
            for md_file in p.glob("**/*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")
                    title = md_file.stem
                    wiki_type = self._guess_type(md_file, content)
                    if wiki_type not in _get_enabled_types():
                        results["skipped"] += 1
                        continue
                    existing = await self._find_by_source(user_id, str(md_file))
                    if existing:
                        await self.update(existing, title=title, content=content)
                    else:
                        await self.add(user_id, wiki_type, title, content, tags=[md_file.parent.name], source=str(md_file))
                    results["imported"] += 1
                except Exception:
                    results["errors"] += 1
        return results

    async def _find_by_source(self, user_id: str, source: str) -> int | None:
        return await find_by_source(self._cm, "user_wiki", user_id, source)

    def _guess_type(self, path: Path, content: str) -> str:
        name = path.stem.lower()
        for t in ALL_WIKI_TYPES:
            if t in name:
                return t
        if any(w in content.lower() for w in ["дневник", "diary", "сегодня"]):
            return "diary"
        if any(w in content.lower() for w in ["проект", "процесс", "задача"]):
            return "work_notes"
        return "diary"

    def _row_to_entry(self, row) -> WikiEntry:
        return WikiEntry(
            entry_id=row["entry_id"],
            user_id=row["user_id"],
            wiki_type=row["wiki_type"],
            title=row["title"],
            content=row["content"],
            tags=parse_tags(row["tags"]),
            importance=row["importance"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
