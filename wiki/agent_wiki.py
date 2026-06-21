"""
Agent Wiki — 7 types of agent identity knowledge
Supports external folders for lore, knowledge bases, style guides
"""
import sqlite3
import time
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class AgentWikiEntry:
    entry_id: int
    user_id: str
    wiki_type: str
    title: str
    content: str
    tags: List[str]
    importance: float
    created_at: float
    updated_at: float


ALL_WIKI_TYPES = ["decision_log", "error_analysis", "personality_evolution", "emotional_context", "wiki_agent", "learning_journal", "principle_log"]


def _get_enabled_types() -> List[str]:
    try:
        import yaml
        config_path = Path(__file__).parent.parent / "config.yaml"
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
        agent_cfg = cfg.get("wiki", {}).get("agent", {})
        return [t for t in ALL_WIKI_TYPES if agent_cfg.get(t, True)]
    except Exception:
        return ALL_WIKI_TYPES


def _get_external_dirs() -> List[str]:
    try:
        import yaml
        config_path = Path(__file__).parent.parent / "config.yaml"
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
        return cfg.get("wiki", {}).get("agent", {}).get("external_dirs", [])
    except Exception:
        return []


class AgentWiki:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(Path.home() / ".mcp-ariel-memory" / "wiki.db")
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_conn()
        try:
            conn.executescript("""
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
            """)
            # Migration: add source column if missing
            try:
                conn.execute("ALTER TABLE agent_wiki ADD COLUMN source TEXT DEFAULT 'manual'")
            except Exception:
                pass
            conn.executescript("""
                CREATE INDEX IF NOT EXISTS idx_awiki_user ON agent_wiki(user_id);
                CREATE INDEX IF NOT EXISTS idx_awiki_type ON agent_wiki(wiki_type);
                CREATE INDEX IF NOT EXISTS idx_awiki_user_type ON agent_wiki(user_id, wiki_type);
                CREATE INDEX IF NOT EXISTS idx_awiki_source ON agent_wiki(source);
            """)
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS agent_wiki_fts USING fts5(
                    title, content, wiki_type,
                    content=agent_wiki,
                    content_rowid=entry_id
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def add(self, user_id: str, wiki_type: str, title: str, content: str,
            tags: List[str] = None, importance: float = 0.5, source: str = "manual") -> int:
        enabled = _get_enabled_types()
        if enabled and wiki_type not in enabled:
            raise ValueError(f"Wiki type '{wiki_type}' is disabled. Enabled: {enabled}")

        conn = self._get_conn()
        try:
            now = time.time()
            cursor = conn.execute(
                "INSERT INTO agent_wiki (user_id, wiki_type, title, content, tags, importance, source, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, wiki_type, title, content, json.dumps(tags or []), importance, source, now, now)
            )
            entry_id = cursor.lastrowid
            conn.execute(
                "INSERT INTO agent_wiki_fts(rowid, title, content, wiki_type) VALUES (?, ?, ?, ?)",
                (entry_id, title, content, wiki_type)
            )
            conn.commit()
            return entry_id
        finally:
            conn.close()

    def update(self, entry_id: int, title: str = None, content: str = None,
               tags: List[str] = None, importance: float = None):
        conn = self._get_conn()
        try:
            updates = ["updated_at=?"]
            params = [time.time()]
            if title:
                updates.append("title=?")
                params.append(title)
            if content:
                updates.append("content=?")
                params.append(content)
            if tags is not None:
                updates.append("tags=?")
                params.append(json.dumps(tags))
            if importance is not None:
                updates.append("importance=?")
                params.append(importance)
            params.append(entry_id)
            conn.execute(f"UPDATE agent_wiki SET {', '.join(updates)} WHERE entry_id=?", params)
            conn.commit()
        finally:
            conn.close()

    def get(self, entry_id: int) -> Optional[AgentWikiEntry]:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM agent_wiki WHERE entry_id=?", (entry_id,)).fetchone()
            return self._row_to_entry(row) if row else None
        finally:
            conn.close()

    def search(self, user_id: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT aw.entry_id, aw.title, aw.content, aw.wiki_type, aw.tags, aw.importance, fts.rank
                   FROM agent_wiki_fts fts JOIN agent_wiki aw ON fts.rowid = aw.entry_id
                   WHERE agent_wiki_fts MATCH ? AND aw.user_id = ?
                   ORDER BY fts.rank DESC LIMIT ?""",
                (query, user_id, limit)
            ).fetchall()
            return [
                {"id": r[0], "title": r[1], "content": r[2][:300], "type": r[3],
                 "tags": json.loads(r[4]) if r[4] else [], "importance": r[5], "score": abs(r[6]) if r[6] else 0}
                for r in rows
            ]
        except Exception:
            return []
        finally:
            conn.close()

    def list_by_type(self, user_id: str, wiki_type: str, limit: int = 20) -> List[AgentWikiEntry]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM agent_wiki WHERE user_id=? AND wiki_type=? ORDER BY updated_at DESC LIMIT ?",
                (user_id, wiki_type, limit)
            ).fetchall()
            return [self._row_to_entry(r) for r in rows]
        finally:
            conn.close()

    def list_all(self, user_id: str, limit: int = 50) -> List[AgentWikiEntry]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM agent_wiki WHERE user_id=? ORDER BY updated_at DESC LIMIT ?",
                (user_id, limit)
            ).fetchall()
            return [self._row_to_entry(r) for r in rows]
        finally:
            conn.close()

    def delete(self, entry_id: int) -> bool:
        conn = self._get_conn()
        try:
            cursor = conn.execute("DELETE FROM agent_wiki WHERE entry_id=?", (entry_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def count(self, user_id: str = None, wiki_type: str = None) -> int:
        conn = self._get_conn()
        try:
            conditions, params = [], []
            if user_id:
                conditions.append("user_id=?")
                params.append(user_id)
            if wiki_type:
                conditions.append("wiki_type=?")
                params.append(wiki_type)
            where = " WHERE " + " AND ".join(conditions) if conditions else ""
            row = conn.execute(f"SELECT COUNT(*) FROM agent_wiki{where}", params).fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    def get_enabled_types(self) -> List[str]:
        return _get_enabled_types()

    def get_external_dirs(self) -> List[str]:
        return _get_external_dirs()

    def sync_external(self, user_id: str) -> Dict[str, int]:
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
                    existing = self._find_by_source(user_id, str(md_file))
                    if existing:
                        self.update(existing, title=title, content=content)
                    else:
                        self.add(user_id, wiki_type, title, content,
                                 tags=[md_file.parent.name], source=str(md_file))
                    results["imported"] += 1
                except Exception:
                    results["errors"] += 1
        return results

    def _find_by_source(self, user_id: str, source: str) -> Optional[int]:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT entry_id FROM agent_wiki WHERE user_id=? AND source=?",
                (user_id, source)
            ).fetchone()
            return row[0] if row else None
        finally:
            conn.close()

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
            entry_id=row["entry_id"], user_id=row["user_id"], wiki_type=row["wiki_type"],
            title=row["title"], content=row["content"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            importance=row["importance"], created_at=row["created_at"], updated_at=row["updated_at"]
        )
