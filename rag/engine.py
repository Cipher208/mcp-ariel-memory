"""
RAG Engine — FTS5 + sqlite-vec hybrid search with embeddings.
All DB operations via AsyncConnectionManager (aiosqlite).
"""
import hashlib
import struct
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

from shared.connection import AsyncConnectionManager, connection_manager


class RAGEngine:
    def __init__(self, cm: Optional[AsyncConnectionManager] = None, layer: str = "user"):
        self._cm = cm or connection_manager
        self.layer = layer
        self._fts_available = False

    async def init_db(self):
        conn = await self._cm.get("memory.db")
        try:
            compile_options = [r[0] for r in await (await conn.execute("PRAGMA compile_options")).fetchall()]
            self._fts_available = "ENABLE_FTS5" in compile_options
        except Exception:
            self._fts_available = False

        await self._cm.execute_script("memory.db", """
            CREATE TABLE IF NOT EXISTS rag_pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                layer TEXT NOT NULL DEFAULT 'user',
                user_id TEXT NOT NULL DEFAULT 'default',
                title TEXT NOT NULL, path TEXT, content TEXT NOT NULL,
                sha256_hash TEXT, wiki_type TEXT,
                created_at REAL DEFAULT (strftime('%s','now')),
                updated_at REAL DEFAULT (strftime('%s','now'))
            );
            CREATE TABLE IF NOT EXISTS rag_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page_id INTEGER NOT NULL, chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL, embedding BLOB
            );
            CREATE TABLE IF NOT EXISTS rag_relations (
                source_id INTEGER NOT NULL, target_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL DEFAULT 'elaborates',
                weight REAL DEFAULT 0.8,
                PRIMARY KEY (source_id, target_id, relation_type)
            );
            CREATE INDEX IF NOT EXISTS idx_rag_user ON rag_pages(user_id);
        """)
        if self._fts_available:
            try:
                await self._cm.execute_script("memory.db",
                    'CREATE VIRTUAL TABLE IF NOT EXISTS rag_fts USING fts5(title, content, wiki_type, content=rag_pages, content_rowid=id)')
            except Exception:
                pass

    async def ingest_file(self, filepath: Path, user_id: str = "default", wiki_type: str = None) -> str:
        content = filepath.read_text(encoding="utf-8")
        file_hash = hashlib.sha256(content.encode()).hexdigest()
        conn = await self._cm.get("memory.db")

        cur = await conn.execute(
            "SELECT id FROM rag_pages WHERE sha256_hash = ? AND user_id = ?", (file_hash, user_id))
        existing = await cur.fetchone()
        if existing:
            return "[SKIP] %s (already ingested)" % filepath.name

        cursor = await conn.execute(
            "INSERT INTO rag_pages (layer, user_id, title, path, content, sha256_hash, wiki_type) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (self.layer, user_id, filepath.stem, str(filepath), content, file_hash, wiki_type))
        page_id = cursor.lastrowid

        if self._fts_available:
            try:
                await conn.execute(
                    "INSERT INTO rag_fts(rowid, title, content, wiki_type) VALUES (?, ?, ?, ?)",
                    (page_id, filepath.stem, content, wiki_type or ""))
            except Exception:
                pass

        chunks = self._chunk_text(content)
        from shared.embeddings import embed_texts
        embeddings = await embed_texts(chunks)
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            blob = struct.pack("%df" % len(emb), *emb) if emb else None
            await conn.execute(
                "INSERT INTO rag_chunks (page_id, chunk_index, content, embedding) VALUES (?, ?, ?, ?)",
                (page_id, i, chunk, blob))

        await conn.commit()
        return "[OK] %s (%d chunks)" % (filepath.name, len(chunks))

    async def ingest_text(self, title: str, text: str, user_id: str = "default",
                    wiki_type: str = None, path: str = "",
                    relation_to: int = None, relation_type: str = "elaborates") -> int:
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        conn = await self._cm.get("memory.db")

        cur = await conn.execute(
            "SELECT id FROM rag_pages WHERE sha256_hash = ? AND user_id = ?", (text_hash, user_id))
        existing = await cur.fetchone()
        if existing:
            return existing[0]

        cursor = await conn.execute(
            "INSERT INTO rag_pages (layer, user_id, title, path, content, sha256_hash, wiki_type) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (self.layer, user_id, title, path, text, text_hash, wiki_type))
        page_id = cursor.lastrowid

        if self._fts_available:
            try:
                await conn.execute(
                    "INSERT INTO rag_fts(rowid, title, content, wiki_type) VALUES (?, ?, ?, ?)",
                    (page_id, title, text, wiki_type or ""))
            except Exception:
                pass

        chunks = self._chunk_text(text)
        from shared.embeddings import embed_texts
        embeddings = await embed_texts(chunks)
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            blob = struct.pack("%df" % len(emb), *emb) if emb else None
            await conn.execute(
                "INSERT INTO rag_chunks (page_id, chunk_index, content, embedding) VALUES (?, ?, ?, ?)",
                (page_id, i, chunk, blob))

        if relation_to is not None:
            await conn.execute(
                "INSERT OR IGNORE INTO rag_relations (source_id, target_id, relation_type) VALUES (?, ?, ?)",
                (page_id, relation_to, relation_type))

        await conn.commit()
        return page_id

    async def search(self, query: str, user_id: str = "default", limit: int = 10) -> List[Dict[str, Any]]:
        conn = await self._cm.get("memory.db")
        if self._fts_available:
            try:
                cur = await conn.execute(
                    """SELECT wp.id, wp.title, wp.content, wp.wiki_type, fts.rank
                       FROM rag_fts fts JOIN rag_pages wp ON fts.rowid = wp.id
                       WHERE rag_fts MATCH ? AND wp.user_id = ?
                       ORDER BY fts.rank DESC LIMIT ?""",
                    (query, user_id, limit))
                rows = await cur.fetchall()
                return [{"id": r[0], "title": r[1],
                         "content": r[2][:500] + "..." if len(r[2]) > 500 else r[2],
                         "wiki_type": r[3], "score": abs(r[4]) if r[4] else 0.0, "source": "fts5"}
                        for r in rows]
            except Exception:
                pass

        # Fallback: LIKE search
        cur = await conn.execute(
            "SELECT id, title, content, wiki_type FROM rag_pages WHERE user_id=? AND (title LIKE ? OR content LIKE ?) LIMIT ?",
            (user_id, "%%%s%%" % query, "%%%s%%" % query, limit))
        rows = await cur.fetchall()
        return [{"id": r[0], "title": r[1],
                 "content": r[2][:500] + "..." if len(r[2]) > 500 else r[2],
                 "wiki_type": r[3], "score": 0.5, "source": "like"}
                for r in rows]

    async def search_rrf(self, query: str, user_id: str = "default", limit: int = 10, k: int = 60) -> List[Dict[str, Any]]:
        fts_results = await self.search(query, user_id, limit=limit * 2)
        fts_ranks = {doc["id"]: rank for rank, doc in enumerate(fts_results)}

        vec_ranks = {}
        try:
            conn = await self._cm.get("memory.db")
            cur = await conn.execute(
                "SELECT wc.page_id, wc.embedding FROM rag_chunks wc "
                "JOIN rag_pages wp ON wc.page_id = wp.id WHERE wp.user_id = ? AND wc.embedding IS NOT NULL",
                (user_id,))
            rows = await cur.fetchall()
            if rows:
                from shared.embeddings import embed_text, similarity
                query_emb = await embed_text(query)
                vec_scores = {}
                for r in rows:
                    page_id, blob = r[0], r[1]
                    chunk_emb = list(struct.unpack("%df" % (len(blob) // 4), blob))
                    sim = similarity(query_emb, chunk_emb)
                    if page_id not in vec_scores or sim > vec_scores[page_id]:
                        vec_scores[page_id] = sim
                vec_sorted = sorted(vec_scores.items(), key=lambda x: -x[1])
                vec_ranks = {pid: rank for rank, (pid, _) in enumerate(vec_sorted[:limit * 2])}
        except Exception:
            pass

        all_ids = set(fts_ranks.keys()) | set(vec_ranks.keys())
        rrf_scores = {}
        for doc_id in all_ids:
            score = 0.0
            if doc_id in fts_ranks:
                score += 1.0 / (k + fts_ranks[doc_id])
            if doc_id in vec_ranks:
                score += 1.0 / (k + vec_ranks[doc_id])
            rrf_scores[doc_id] = score

        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: -rrf_scores[x])[:limit]
        conn = await self._cm.get("memory.db")
        results = []
        for doc_id in sorted_ids:
            row = await (await conn.execute(
                "SELECT id, title, content, wiki_type FROM rag_pages WHERE id=?", (doc_id,))).fetchone()
            if row:
                has_fts = doc_id in fts_ranks
                has_vec = doc_id in vec_ranks
                source = "rrf(fts+vec)" if (has_fts and has_vec) else ("fts5" if has_fts else "vec")
                results.append({"id": row[0], "title": row[1],
                                "content": row[2][:500] + "..." if len(row[2]) > 500 else row[2],
                                "wiki_type": row[3], "score": rrf_scores[doc_id], "source": source})
        return results

    async def get_relations(self, page_id: int, depth: int = 1) -> List[Dict[str, Any]]:
        conn = await self._cm.get("memory.db")
        sql = """
        WITH RECURSIVE graph AS (
            SELECT r.source_id, r.target_id, r.relation_type, r.weight, 1 as d
            FROM rag_relations r WHERE r.source_id = ?
            UNION ALL
            SELECT r.source_id, r.target_id, r.relation_type, r.weight, g.d + 1
            FROM rag_relations r JOIN graph g ON r.source_id = g.target_id WHERE g.d < ?
        )
        SELECT wp.id, wp.title, g.relation_type, g.weight
        FROM graph g JOIN rag_pages wp ON g.target_id = wp.id
        """
        cur = await conn.execute(sql, (page_id, depth))
        rows = await cur.fetchall()
        return [{"id": r[0], "title": r[1], "relation": r[2], "weight": r[3]} for r in rows]

    async def add_relation(self, source_id: int, target_id: int, relation_type: str = "elaborates", weight: float = 0.8):
        conn = await self._cm.get("memory.db")
        await conn.execute(
            "INSERT OR REPLACE INTO rag_relations (source_id, target_id, relation_type, weight) VALUES (?, ?, ?, ?)",
            (source_id, target_id, relation_type, weight))
        await conn.commit()

    async def count_pages(self, user_id: str = None) -> int:
        conn = await self._cm.get("memory.db")
        if user_id:
            row = await (await conn.execute("SELECT COUNT(*) FROM rag_pages WHERE user_id=?", (user_id,))).fetchone()
        else:
            row = await (await conn.execute("SELECT COUNT(*) FROM rag_pages")).fetchone()
        return row[0] if row else 0

    async def count_chunks(self) -> int:
        conn = await self._cm.get("memory.db")
        row = await (await conn.execute("SELECT COUNT(*) FROM rag_chunks")).fetchone()
        return row[0] if row else 0

    def _chunk_text(self, text: str, max_size: int = 500, overlap: int = 100) -> List[str]:
        paragraphs = text.split("\n\n")
        chunks, current = [], ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(current) + len(para) + 2 <= max_size:
                current = "%s\n\n%s" % (current, para) if current else para
            else:
                if current:
                    chunks.append(current)
                if len(para) > max_size:
                    words = para.split()
                    current = ""
                    for word in words:
                        if len(current) + len(word) + 1 <= max_size:
                            current = ("%s %s" % (current, word)) if current else word
                        else:
                            if current:
                                chunks.append(current)
                            current = word
                else:
                    current = para
        if current:
            chunks.append(current)
        return chunks
