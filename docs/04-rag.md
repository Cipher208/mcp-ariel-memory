# Поиск (RAG) — rag/ (async, embeddings в БД)

## RAGEngine (`rag/engine.py`)

FTS5 + RRF + fallback на LIKE. Эмбеддинги записываются при ingest и читаются из БД при поиске.

### SHA256 дедупликация

Файл с тем же SHA256 хешем пропускается при ingest:

```python
text_hash = hashlib.sha256(text.encode()).hexdigest()
existing = await conn.execute(
    "SELECT id FROM rag_pages WHERE sha256_hash = ? AND user_id = ?",
    (text_hash, user_id)).fetchone()
if existing:
    return existing[0]  # skip — уже индексировано
```

### WAL journal mode

Все SQLite соединения используют WAL для конкурентного чтения. Настроено в `AsyncConnectionManager`:

```python
await conn.execute("PRAGMA journal_mode=WAL")
await conn.execute("PRAGMA busy_timeout=5000")
await conn.execute("PRAGMA synchronous=NORMAL")
```

```python
from rag.engine import RAGEngine

rag = RAGEngine(layer="user")

# Индексация (эмбеддинги вычисляются и сохраняются в rag_chunks.embedding)
await rag.ingest_text("Architecture", "Two-layer memory", user_id="alice")
await rag.ingest_file(Path("docs/design.md"), user_id="alice")

# Поиск (эмбеддинги читаются из БД, не вычисляются заново)
results = await rag.search("memory architecture", user_id="alice", limit=5)
results = await rag.search_rrf("memory architecture", user_id="alice", limit=5)

# RRF результаты:
# [{"title": "...", "score": 0.0325, "source": "rrf(fts+vec)"}]
# source: "fts5", "vec", или "rrf(fts+vec)"
```

**Архитектура поиска:**
- `search()` — FTS5 полнотекстовый (fallback на LIKE)
- `search_rrf()` — Reciprocal Rank Fusion: FTS5 + vector similarity
- Эмбеддинги: вычисляются 1 раз при ingest, хранятся в `rag_chunks.embedding`
- При поиске: читаются из БД → O(1) вместо O(N)

## RetrievalRouter (`rag/router.py`)

```python
from rag.router import RetrievalRouter

router = RetrievalRouter(user_id="alice")
result = await router.route("How to configure Redis?")
# result.strategy, result.context, result.confidence
```
rag.ingest_file(Path("docs/design.md"), user_id="alice")

# Обычный FTS5 поиск
results = rag.search("memory architecture", user_id="alice", limit=5)

# RRF — гибридный поиск (FTS5 + vector similarity)
results = rag.search_rrf("memory architecture", user_id="alice", limit=5)
# [{"id": 1, "title": "Architecture", "content": "...", "score": 0.0325, "source": "rrf(fts+vec)"}]

rag.add_relation(page1_id, page2_id, "elaborates", weight=0.8)
rag.get_relations(page1_id, depth=2)
rag.count_pages("alice")
rag.count_chunks()
```

### RRF (Reciprocal Rank Fusion)

Комбинирует два источника:
- FTS5 (полнотекстовый поиск)
- Vector similarity (embedding cosine similarity)

Формула: `score = sum(1 / (k + rank_i))` где k=60

**Источники в ответе:**
- `fts5` — только FTS5 результат
- `vec` — только vector результат
- `rrf(fts+vec)` — комбинированный

**Fallback:** если vector search недоступен, используется чистый FTS5.

## RetrievalRouter (`rag/router.py`)

Роутер запросов: определяет стратегию поиска.

```python
from rag.router import RetrievalRouter

router = RetrievalRouter(user_id="alice")
result = router.route("How to configure Redis?")
# result.strategy = Strategy.WIKI
# result.context = [{"title": "...", "content": "...", "score": 0.95}]
# result.confidence = 0.95
```

**Стратегии:**

| Стратегия | Статус | Когда | Источник |
|-----------|--------|-------|----------|
| `L1_BUFFER` | ✅ | Недавние контекстные вопросы | L1 буфер |
| `SEMANTIC` | ✅ | Общие запросы | FTS5 + RRF |
| `WIKI` | ✅ | Технические вопросы | Wiki + relations |
| `GRAPH` | 🔲 Planned | Запросы к графу | EpistemicGraph (enum есть, route() не возвращает) |

## ConflictResolver (`rag/conflict.py`)

Обнаружение конфликтующих записей.

```python
from rag.conflict import ConflictResolver

cr = ConflictResolver()
result = cr.check("alice", "Python is the best language")
# {"is_conflict": False}

result2 = cr.check("alice", "Python is best for coding")
# {"is_conflict": True, "conflict_group_id": "abc-123", "similarity": 0.6}

cr.resolve("abc-123", keep_id=1)
```
