"""
Embeddings module — multilingual sentence embeddings with SQLite cache.
Модель: intfloat/multilingual-e5-small (384 dim, поддерживает 100+ языков включая русский).
"""
import hashlib
import sqlite3
import struct
import time
from pathlib import Path
from typing import List, Optional

_model = None
_model_name = None

DEFAULT_MODEL = "intfloat/multilingual-e5-small"  # 384 dim, 100+ языков


def _get_model(model_name: str = None):
    global _model, _model_name
    target = model_name or DEFAULT_MODEL
    if _model is None or _model_name != target:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(target)
            _model_name = target
        except ImportError:
            _model = False
    return _model


class EmbeddingCache:
    """SQLite-кэш эмбеддингов (SHA-256 → blob).
    Модель по умолчанию: intfloat/multilingual-e5-small (384 dim, 100+ языков).
    """

    def __init__(self, db_path: str = None, model_name: str = None):
        self.db_path = db_path or str(Path.home() / ".mcp-ariel-memory" / "embedding_cache.db")
        self.model_name = model_name or DEFAULT_MODEL
        self._dimension = 384
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS embedding_cache (
                    text_hash TEXT PRIMARY KEY,
                    embedding BLOB NOT NULL,
                    model_name TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
        finally:
            conn.close()

    def _normalize_text(self, text: str) -> str:
        """Нормализация текста перед хешированием: lowercase, убрать пунктуацию, пробелы."""
        import re
        text = text.lower().strip()
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text

    def _hash_text(self, text: str) -> str:
        normalized = self._normalize_text(text)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _get_cached(self, text: str) -> Optional[List[float]]:
        text_hash = self._hash_text(text)
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT embedding FROM embedding_cache WHERE text_hash=? AND model_name=?",
                (text_hash, self.model_name)
            ).fetchone()
            if row:
                blob = row[0]
                return list(struct.unpack("%df" % (len(blob) // 4), blob))
        except Exception:
            pass
        finally:
            conn.close()
        return None

    def _cache(self, text: str, embedding: List[float]):
        text_hash = self._hash_text(text)
        blob = struct.pack("%df" % len(embedding), *embedding)
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO embedding_cache (text_hash, embedding, model_name) VALUES (?, ?, ?)",
                (text_hash, blob, self.model_name)
            )
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        model = _get_model()
        results = [None] * len(texts)
        to_compute = []

        for i, text in enumerate(texts):
            cached = self._get_cached(text)
            if cached is not None:
                results[i] = cached
            else:
                to_compute.append((i, text))

        if to_compute and model:
            compute_texts = [t for _, t in to_compute]
            embeddings = model.encode(compute_texts).tolist()
            for (idx, text), emb in zip(to_compute, embeddings):
                results[idx] = emb
                self._cache(text, emb)
        elif to_compute:
            for idx, text in to_compute:
                emb = _hash_embedding(text)
                results[idx] = emb
                self._cache(text, emb)

        return [r if r is not None else [0.0] * self._dimension for r in results]

    def embed_single(self, text: str) -> List[float]:
        return self.embed([text])[0]

    def clear(self):
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM embedding_cache")
            conn.commit()
        finally:
            conn.close()

    def count(self) -> int:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT COUNT(*) FROM embedding_cache").fetchone()
            return row[0] if row else 0
        finally:
            conn.close()


def embed_text(text: str) -> List[float]:
    """Generate embedding for a single text (with cache)."""
    cache = EmbeddingCache()
    return cache.embed_single(text)


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for multiple texts (with cache)."""
    cache = EmbeddingCache()
    return cache.embed(texts)


def similarity(a: List[float], b: List[float]) -> float:
    """Cosine similarity between two embeddings."""
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _hash_embedding(text: str, dim: int = 384) -> List[float]:
    """Deterministic hash-based embedding (fallback when no model)."""
    h = hashlib.sha512(text.lower().encode()).digest()
    floats = []
    for i in range(0, len(h) - 3, 4):
        if len(floats) >= dim:
            break
        val = struct.unpack("f", h[i:i + 4])[0]
        if abs(val) < 1e10:
            floats.append(val)
    while len(floats) < dim:
        floats.append(0.0)
    norm = sum(x * x for x in floats) ** 0.5
    if norm > 0:
        floats = [x / norm for x in floats]
    return floats[:dim]
