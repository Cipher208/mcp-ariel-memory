"""
Agent Wiki — 7 types of agent identity knowledge
Supports external folders for lore, knowledge bases, style guides
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
class AgentWikiEntry:
    entry_id: int
    user_id: str
    wiki_type: str
    title: str
    content: str
    tags: list[str]
    importance: float
    created_at: float
    updated_at: float


ALL_WIKI_TYPES = [
    "decision_log",
    "error_analysis",
    "personality_evolution",
    "emotional_context",
    "wiki_agent",
    "learning_journal",
    "principle_log",
]


def _get_enabled_types() -> list[str]:
    return get_enabled_types("agent", ALL_WIKI_TYPES)


def _get_external_dirs() -> list[str]:
    return get_external_dirs("agent")


class AgentWiki:
    def __init__(self, cm: AsyncConnectionManager = None):
        self._cm = cm or connection_manager

    async def init_db(self):
        await self._cm.execute_script(
            "memory.db",
            """
            CREATE TABLE IF NOT EXISTS agent_wiki (
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
            CREATE INDEX IF NOT EXISTS idx_awiki_user ON agent_wiki(user_id);
            CREATE INDEX IF NOT EXISTS idx_awiki_type ON agent_wiki(wiki_type);
            CREATE INDEX IF NOT EXISTS idx_awiki_user_type ON agent_wiki(user_id, wiki_type);
            CREATE INDEX IF NOT EXISTS idx_awiki_source ON agent_wiki(source);
            CREATE INDEX IF NOT EXISTS idx_awiki_updated ON agent_wiki(updated_at);
        """,
        )
        conn = await self._cm.get("memory.db")
        try:
            await conn.execute("ALTER TABLE agent_wiki ADD COLUMN source TEXT DEFAULT 'manual'")
        except Exception:
            pass
        await conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS agent_wiki_fts USING fts5(
                title, content, wiki_type,
                content=agent_wiki,
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
            "INSERT INTO agent_wiki (user_id, wiki_type, title, content, tags, importance, source, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, wiki_type, title, content, json.dumps(tags or []), importance, source, now, now),
        )
        entry_id = cur.lastrowid
        await conn.execute(
            "INSERT INTO agent_wiki_fts(rowid, title, content, wiki_type) VALUES (?, ?, ?, ?)",
            (entry_id, title, content, wiki_type),
        )
        await conn.commit()
        return entry_id

    async def update(self, entry_id: int, title: str = None, content: str = None, tags: list[str] = None, importance: float = None):
        conn = await self._cm.get("memory.db")
        updates, params = build_update_clause({"title": title, "content": content, "tags": tags, "importance": importance})
        params.append(entry_id)
        await conn.execute(f"UPDATE agent_wiki SET {', '.join(updates)} WHERE entry_id=?", params)
        await conn.commit()

    async def get(self, entry_id: int) -> AgentWikiEntry | None:
        conn = await self._cm.get("memory.db")
        cur = await conn.execute("SELECT * FROM agent_wiki WHERE entry_id=?", (entry_id,))
        row = await cur.fetchone()
        return self._row_to_entry(row) if row else None

    async def search(self, user_id: str, query: str, limit: int = 10) -> list[dict[str, Any]]:
        try:
            conn = await self._cm.get("memory.db")
            cur = await conn.execute(
                """SELECT aw.entry_id, aw.title, aw.content, aw.wiki_type, aw.tags, aw.importance, fts.rank
                   FROM agent_wiki_fts fts JOIN agent_wiki aw ON fts.rowid = aw.entry_id
                   WHERE agent_wiki_fts MATCH ? AND aw.user_id = ?
                   ORDER BY fts.rank DESC LIMIT ?""",
                (query, user_id, limit),
            )
            rows = await cur.fetchall()
            return [format_search_result(r) for r in rows]
        except Exception:
            return []

    async def list_by_type(self, user_id: str, wiki_type: str, limit: int = 20) -> list[AgentWikiEntry]:
        conn = await self._cm.get("memory.db")
        cur = await conn.execute(
            "SELECT * FROM agent_wiki WHERE user_id=? AND wiki_type=? ORDER BY updated_at DESC LIMIT ?",
            (user_id, wiki_type, limit),
        )
        rows = await cur.fetchall()
        return [self._row_to_entry(r) for r in rows]

    async def list_all(self, user_id: str, limit: int = 50) -> list[AgentWikiEntry]:
        conn = await self._cm.get("memory.db")
        cur = await conn.execute("SELECT * FROM agent_wiki WHERE user_id=? ORDER BY updated_at DESC LIMIT ?", (user_id, limit))
        rows = await cur.fetchall()
        return [self._row_to_entry(r) for r in rows]

    async def delete(self, entry_id: int) -> bool:
        conn = await self._cm.get("memory.db")
        cur = await conn.execute("DELETE FROM agent_wiki WHERE entry_id=?", (entry_id,))
        await conn.commit()
        return cur.rowcount > 0

    async def count(self, user_id: str = None, wiki_type: str = None) -> int:
        conn = await self._cm.get("memory.db")
        query, params = build_count_query("agent_wiki", user_id, wiki_type)
        cur = await conn.execute(query, params)
        row = await cur.fetchone()
        return row[0] if row else 0

    def get_enabled_types(self) -> list[str]:
        return _get_enabled_types()

    def get_external_dirs(self) -> list[str]:
        return _get_external_dirs()

    async def sync_external(self, user_id: str) -> dict[str, int]:
        """Sync external .md files (lore, knowledge bases, style guides) into wiki."""
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
        return await find_by_source(self._cm, "agent_wiki", user_id, source)

    def _guess_type(self, path: Path, content: str) -> str:
        name = path.stem.lower()
        parent = path.parent.name.lower()

        if any(w in name or w in parent for w in ["lore", "лор", "world", "мир"]):
            return "wiki_agent"
        if any(w in name or w in parent for w in ["knowledge", "знани", "reference", "справочник"]):
            return "wiki_agent"
        if any(w in name or w in parent for w in ["style", "стиль", "guide", "гайд"]):
            return "personality_evolution"
        if any(w in name or w in parent for w in ["error", "ошибк", "bug"]):
            return "error_analysis"
        if any(w in name or w in parent for w in ["decision", "решени", "choice"]):
            return "decision_log"
        if any(w in name or w in parent for w in ["learning", "обучен", "learn"]):
            return "learning_journal"
        if any(w in name or w in parent for w in ["principle", "принцип", "rule", "правило"]):
            return "principle_log"

        if any(w in content.lower() for w in ["решение", "decided", "chose"]):
            return "decision_log"
        if any(w in content.lower() for w in ["ошибка", "error", "bug", "исправил"]):
            return "error_analysis"
        if any(w in content.lower() for w in ["принцип", "principle", "всегда", "никогда"]):
            return "principle_log"

        return "wiki_agent"

    def _row_to_entry(self, row) -> AgentWikiEntry:
        return AgentWikiEntry(
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
