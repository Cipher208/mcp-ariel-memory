"""
RAG Engine — FTS5 + binary embeddings hybrid search.
All DB operations via AsyncConnectionManager (aiosqlite).
"""

import hashlib
import logging
import struct
import warnings
from pathlib import Path
from typing import Any, Literal, Optional

from shared.connection import AsyncConnectionManager, connection_manager
from config import config as _config

logger = logging.getLogger(__name__)

try:
    from rag.quantize import embed_to_binary, hamming_distance, hamming_to_score

    _HAS_BINARY = True
except ImportError:
    _HAS_BINARY = False

StrategyT = Literal["fts", "mib", "hybrid", "auto"]


class RAGEngine:
    def __init__(
        self,
        cm: AsyncConnectionManager | None = None,
        layer: str = "user",
        binary_dim: int = 384,
        binary_threshold_mode: str = "naive",
        binary_thresholds_path: Optional[str] = None,
        thresholds=None,
        search_strategy: StrategyT = "fts",
    ):
        self._cm = cm or connection_manager
        self.layer = layer
        self._fts_available = False
        self.binary_dim = binary_dim
        self.binary_threshold_mode = binary_threshold_mode
        self.binary_thresholds_path = binary_thresholds_path
        self._thresholds_cache = None
        self.thresholds = thresholds
        self.search_strategy: StrategyT = search_strategy
        self.scorer = None  # lazily set from rag.scoring if needed

    def _rrf_k(self) -> int:
        """Get RRF k parameter from config (default 60)."""
        try:
            from config import config

            return int(config.get("rag", "rrf_k", default=60))
        except Exception:
            return 60

    def _load_thresholds(self):
        """Load supervised thresholds if available. Returns None for naive mode."""
        if self.binary_threshold_mode != "supervised_path":
            return None
        if self._thresholds_cache is not None:
            return self._thresholds_cache
        if not self.binary_thresholds_path:
            return None
        try:
            import numpy as np

            self._thresholds_cache = np.load(self.binary_thresholds_path)
        except (FileNotFoundError, Exception):
            return None
        return self._thresholds_cache

    def _binary_for(self, emb: list[float]) -> bytes:
        """Convert embedding to binary using configured mode."""
        if not _HAS_BINARY:
            return None
        thr = self.thresholds if self.thresholds is not None else self._load_thresholds()
        if thr is not None:
            from rag.quantize import binary_from_threshold_array

            return binary_from_threshold_array(emb, thr)
        return embed_to_binary(emb, threshold=0.0, dim=len(emb))

    async def init_db(self):
        conn = await self._cm.get("memory.db")
        try:
            compile_options = [r[0] for r in await (await conn.execute("PRAGMA compile_options")).fetchall()]
            self._fts_available = "ENABLE_FTS5" in compile_options
        except Exception:
            self._fts_available = False

        if not self._fts_available:
            from shared.metrics import metrics

            metrics.inc("rag_fts5_unavailable_total")
            metrics.gauge("rag_fts5_enabled", 0)
            logger.warning(
                "[rag] SQLite build lacks FTS5; lexical search will use LIKE fallback. Install sqlite3 with FTS5 support for better search quality."
            )

        await self._cm.execute_script(
            "memory.db",
            """
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
                content TEXT NOT NULL, embedding BLOB, bin_embedding BLOB
            );
            CREATE TABLE IF NOT EXISTS rag_relations (
                source_id INTEGER NOT NULL, target_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL DEFAULT 'elaborates',
                weight REAL DEFAULT 0.8,
                PRIMARY KEY (source_id, target_id, relation_type)
            );
            CREATE INDEX IF NOT EXISTS idx_rag_user ON rag_pages(user_id);
            CREATE INDEX IF NOT EXISTS idx_rag_chunks_bin ON rag_chunks(page_id, id) WHERE bin_embedding IS NOT NULL;
        """,
        )
        if self._fts_available:
            try:
                await self._cm.execute_script(
                    "memory.db",
                    "CREATE VIRTUAL TABLE IF NOT EXISTS rag_fts USING fts5(title, content, wiki_type, content=rag_pages, content_rowid=id)",
                )
            except Exception:
                pass

    async def ingest_file(self, filepath: Path, user_id: str = "default", wiki_type: str = None) -> str:
        content = filepath.read_text(encoding="utf-8")
        file_hash = hashlib.sha256(content.encode()).hexdigest()
        conn = await self._cm.get("memory.db")

        cur = await conn.execute("SELECT id FROM rag_pages WHERE sha256_hash = ? AND user_id = ?", (file_hash, user_id))
        existing = await cur.fetchone()
        if existing:
            return "[SKIP] %s (already ingested)" % filepath.name

        cursor = await conn.execute(
            "INSERT INTO rag_pages (layer, user_id, title, path, content, sha256_hash, wiki_type) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (self.layer, user_id, filepath.stem, str(filepath), content, file_hash, wiki_type),
        )
        page_id = cursor.lastrowid

        if self._fts_available:
            try:
                await conn.execute(
                    "INSERT INTO rag_fts(rowid, title, content, wiki_type) VALUES (?, ?, ?, ?)",
                    (page_id, filepath.stem, content, wiki_type or ""),
                )
            except Exception:
                pass

        chunks = self._chunk_text(content)
        from shared.embeddings import embed_texts

        embeddings = await embed_texts(chunks)
        keep_floats = _config.get("rag", "storage", "keep_float_blobs", default=True)
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            float_blob = struct.pack("%df" % len(emb), *emb) if emb and keep_floats else None
            bin_blob = self._binary_for(emb) if emb and _HAS_BINARY else None
            await conn.execute(
                "INSERT INTO rag_chunks (page_id, chunk_index, content, embedding, bin_embedding) VALUES (?, ?, ?, ?, ?)",
                (page_id, i, chunk, float_blob, bin_blob),
            )

        await conn.commit()
        return "[OK] %s (%d chunks)" % (filepath.name, len(chunks))

    async def ingest_text(
        self,
        title: str,
        text: str,
        user_id: str = "default",
        wiki_type: str = None,
        path: str = "",
        relation_to: int = None,
        relation_type: str = "elaborates",
    ) -> int:
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        conn = await self._cm.get("memory.db")

        cur = await conn.execute("SELECT id FROM rag_pages WHERE sha256_hash = ? AND user_id = ?", (text_hash, user_id))
        existing = await cur.fetchone()
        if existing:
            return existing[0]

        cursor = await conn.execute(
            "INSERT INTO rag_pages (layer, user_id, title, path, content, sha256_hash, wiki_type) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (self.layer, user_id, title, path, text, text_hash, wiki_type),
        )
        page_id = cursor.lastrowid

        if self._fts_available:
            try:
                await conn.execute(
                    "INSERT INTO rag_fts(rowid, title, content, wiki_type) VALUES (?, ?, ?, ?)",
                    (page_id, title, text, wiki_type or ""),
                )
            except Exception:
                pass

        chunks = self._chunk_text(text)
        from shared.embeddings import embed_texts

        embeddings = await embed_texts(chunks)
        keep_floats = _config.get("rag", "storage", "keep_float_blobs", default=True)
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            float_blob = struct.pack("%df" % len(emb), *emb) if emb and keep_floats else None
            bin_blob = self._binary_for(emb) if emb and _HAS_BINARY else None
            await conn.execute(
                "INSERT INTO rag_chunks (page_id, chunk_index, content, embedding, bin_embedding) VALUES (?, ?, ?, ?, ?)",
                (page_id, i, chunk, float_blob, bin_blob),
            )

        if relation_to is not None:
            await conn.execute(
                "INSERT OR IGNORE INTO rag_relations (source_id, target_id, relation_type) VALUES (?, ?, ?)",
                (page_id, relation_to, relation_type),
            )

        await conn.commit()
        return page_id

    async def search(
        self,
        query: str,
        user_id: str = "default",
        strategy: Optional[StrategyT] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        strategy = strategy or self.search_strategy
        if strategy == "auto":
            strategy = self._auto_strategy(query)
        if strategy == "fts":
            return await self._search_fts5(query, user_id, limit)
        elif strategy == "mib":
            return await self._search_binary(query, user_id, limit)
        elif strategy == "hybrid":
            return await self._search_hybrid(query, user_id, limit)
        else:
            raise ValueError(f"unknown strategy: {strategy!r}")

    def _auto_strategy(self, query: str) -> str:
        if len(query.split()) <= 2:
            return "fts"
        return "hybrid"

    async def _search_fts5(self, query: str, user_id: str = "default", limit: int = 10) -> list[dict[str, Any]]:
        conn = await self._cm.get("memory.db")
        if self._fts_available:
            try:
                cur = await conn.execute(
                    """SELECT wp.id, wp.title, wp.content, wp.wiki_type, fts.rank
                       FROM rag_fts fts JOIN rag_pages wp ON fts.rowid = wp.id
                       WHERE rag_fts MATCH ? AND wp.user_id = ?
                       ORDER BY fts.rank DESC LIMIT ?""",
                    (query, user_id, limit),
                )
                rows = await cur.fetchall()
                return [
                    {
                        "id": r[0],
                        "title": r[1],
                        "content": r[2][:500] + "..." if len(r[2]) > 500 else r[2],
                        "wiki_type": r[3],
                        "score": abs(r[4]) if r[4] else 0.0,
                        "source": "fts5",
                    }
                    for r in rows
                ]
            except Exception:
                pass

        cur = await conn.execute(
            "SELECT id, title, content, wiki_type FROM rag_pages WHERE user_id=? AND (title LIKE ? OR content LIKE ?) LIMIT ?",
            (user_id, "%%%s%%" % query, "%%%s%%" % query, limit),
        )
        rows = await cur.fetchall()
        return [
            {
                "id": r[0],
                "page_id": r[0],
                "title": r[1] or "",
                "content": r[2] or "",  # Full content, no truncation
                "wiki_type": r[3],
                "score": None,  # NOT 0.5 — caller knows this is degraded
                "source": "fts5_like_fallback",
            }
            for r in rows
        ]

    async def _search_hybrid(self, query: str, user_id: str = "default", limit: int = 10) -> list[dict[str, Any]]:
        fts = await self._search_fts5(query, user_id, limit * 3)
        mib = await self._search_binary(query, user_id, limit * 3)
        candidates = self._materialize_candidates(fts + mib)
        if self.scorer is not None:
            ranked = await self.scorer.rank(query, candidates, user_id)
        else:
            ranked = sorted(candidates, key=lambda c: -(c.rrf_score or 0.0))
        return [self._format_result(c) for c in ranked][:limit]

    async def _search_binary(
        self,
        query: str,
        user_id: str = "default",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Exhaustive linear scan over binary embeddings.

        Requires numpy. 100% recall (deterministic). On 10K chunks
        ~30-100ms single-threaded with numpy, ~5x faster with cache-friendly batching.
        """
        if not _HAS_BINARY:
            return []

        from shared.embeddings import embed_text

        q_emb = await embed_text(query)
        q_bin = self._binary_for(q_emb)
        if q_bin is None:
            return []

        conn = await self._cm.get("memory.db")
        rows = await (
            await conn.execute(
                """
            SELECT c.id, c.page_id, c.content, c.bin_embedding,
                   p.title, p.wiki_type
            FROM rag_chunks c
            JOIN rag_pages p ON p.id = c.page_id
            WHERE p.user_id = ?
              AND c.bin_embedding IS NOT NULL
            """,
                (user_id,),
            )
        ).fetchall()

        scored = []
        for r in rows:
            d = hamming_distance(q_bin, r["bin_embedding"])
            scored.append(
                {
                    "id": r["id"],
                    "page_id": r["page_id"],
                    "title": r["title"],
                    "content": r["content"][:1024],
                    "wiki_type": r["wiki_type"],
                    "score": hamming_to_score(d, self.binary_dim),
                    "source": "mib",
                }
            )
        scored.sort(key=lambda x: (-x["score"], x["id"]))
        return scored[:limit]

    async def _search_rrf(self, query: str, user_id: str = "default", limit: int = 10, k: int = 60) -> list[dict[str, Any]]:
        fts_results = await self._search_fts5(query, user_id, limit=limit * 3)
        fts_ranks = {doc["id"]: rank for rank, doc in enumerate(fts_results)}

        bin_ranks = {}
        try:
            bin_results = await self._search_binary(query, user_id=user_id, limit=limit * 3)
            bin_ranks = {r["id"]: rank for rank, r in enumerate(bin_results)}
        except Exception:
            pass

        # Reciprocal Rank Fusion
        def rrf(rank: int) -> float:
            return 1.0 / (k + rank + 1)

        merged = {}
        for doc_id in set(fts_ranks.keys()) | set(bin_ranks.keys()):
            score = 0.0
            if doc_id in fts_ranks:
                score += rrf(fts_ranks[doc_id])
            if doc_id in bin_ranks:
                score += rrf(bin_ranks[doc_id])
            merged[doc_id] = score

        sorted_ids = sorted(merged.keys(), key=lambda x: -merged[x])[:limit]
        conn = await self._cm.get("memory.db")
        results = []
        for doc_id in sorted_ids:
            row = await (await conn.execute("SELECT id, title, content, wiki_type FROM rag_pages WHERE id=?", (doc_id,))).fetchone()
            if row:
                has_fts = doc_id in fts_ranks
                has_bin = doc_id in bin_ranks
                source = "rrf(fts+mib)" if (has_fts and has_bin) else ("fts5" if has_fts else "mib")
                results.append(
                    {
                        "id": row[0],
                        "title": row[1],
                        "content": row[2][:500] + "..." if len(row[2]) > 500 else row[2],
                        "wiki_type": row[3],
                        "score": merged[doc_id],
                        "source": source,
                    }
                )
        return results

    def _materialize_candidates(self, results: list[dict[str, Any]]) -> list:
        """Convert raw search dicts to ScoredCandidate objects for the Scorer."""
        from rag.scoring import ScoredCandidate

        seen: dict[int, ScoredCandidate] = {}
        for r in results:
            rid = r["id"]
            if rid in seen:
                existing = seen[rid]
                if r.get("source") == "mib" and existing.bin_score is None:
                    existing.bin_score = r["score"]
                if r["score"] is not None:
                    existing.rrf_score = max(existing.rrf_score or 0.0, r["score"])
            else:
                seen[rid] = ScoredCandidate(
                    id=rid,
                    page_id=r.get("page_id", rid),
                    title=r["title"],
                    content=r["content"],
                    wiki_type=r.get("wiki_type"),
                    rrf_score=r["score"] or 0.0,
                    bin_score=r["score"] if r.get("source") == "mib" else None,
                    source=r.get("source", ""),
                )
        return list(seen.values())

    def _format_result(self, c) -> dict[str, Any]:
        """Convert a ScoredCandidate back to a result dict."""
        content = c.content
        if len(content) > 500:
            content = content[:500] + "..."
        return {
            "id": c.id,
            "title": c.title,
            "content": content,
            "wiki_type": c.wiki_type,
            "score": c.final_score if c.final_score else c.rrf_score,
            "source": c.source,
        }

    async def search_rrf(self, *args, **kwargs) -> list[dict[str, Any]]:
        warnings.warn("search_rrf() deprecated; use search(strategy='hybrid')", DeprecationWarning, stacklevel=2)
        return await self.search(strategy="hybrid", *args, **kwargs)

    async def search_binary(self, *args, **kwargs) -> list[dict[str, Any]]:
        warnings.warn("search_binary() deprecated; use search(strategy='mib')", DeprecationWarning, stacklevel=2)
        return await self.search(strategy="mib", *args, **kwargs)

    async def get_relations(self, page_id: int, depth: int = 1) -> list[dict[str, Any]]:
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
            (source_id, target_id, relation_type, weight),
        )
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

    def _chunk_text(self, text: str, max_size: int = 500, overlap: int = 100) -> list[str]:
        """Split text into chunks with sliding overlap for semantic continuity.

        Rules:
          1. Split on double newline (paragraph).
          2. When accumulated buffer reaches max_size, flush it.
             Last `overlap` chars carry over to next chunk.
          3. Paragraphs longer than max_size are split by words
             (overlap only at paragraph boundaries, not within).
        """
        if overlap >= max_size:
            raise ValueError("overlap=%d must be < max_size=%d" % (overlap, max_size))

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks: list[str] = []
        buffer: list[str] = []

        def _flush(buf: list[str]) -> None:
            if not buf:
                return
            chunks.append("\n\n".join(buf).strip())

        def _take_overlap(buf: list[str], n: int) -> list[str]:
            """Return last n chars of joined buffer as leading part for next chunk."""
            if n <= 0 or not buf:
                return []
            joined = "\n\n".join(buf)
            tail = joined[-n:]
            return [tail]

        for p in paragraphs:
            if len(p) > max_size:
                # Flush current buffer first
                _flush(buffer)
                buffer = []
                # Split long paragraph by words
                words = p.split()
                word_buf: list[str] = []
                for w in words:
                    if len(" ".join(word_buf + [w])) > max_size and word_buf:
                        chunks.append(" ".join(word_buf).strip())
                        # Word-level overlap: keep last N words
                        word_buf = word_buf[-max(1, overlap // 8) :] + [w] if overlap else [w]
                    else:
                        word_buf.append(w)
                if word_buf:
                    chunks.append(" ".join(word_buf).strip())
                continue

            projected = "\n\n".join(buffer + [p])
            if len(projected) > max_size and buffer:
                _flush(buffer)
                buffer = _take_overlap(buffer, overlap)
            buffer.append(p)

        _flush(buffer)
        return chunks
