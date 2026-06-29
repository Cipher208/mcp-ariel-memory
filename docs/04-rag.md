# RAG Module — rag/

Hybrid search (FTS5 + binary embeddings) with entity routing, conflict detection, and graph-based retrieval. All database operations use `AsyncConnectionManager` (aiosqlite) with WAL journal mode.

## Unified Search API

The RAG engine provides a **single `search()` method** with pluggable strategies. All strategies share the same result format and can be combined with the unified `Scorer` for advanced ranking.

### Search Strategies

| Strategy | Description | When to Use |
|----------|-------------|-------------|
| `fts` | Full-text search via FTS5 with LIKE fallback | Short queries (<3 words), keyword-heavy searches |
| `mib` | Binary embedding similarity (Hamming distance) | Semantic similarity, concept-based queries |
| `hybrid` | Combines FTS5 + MIB with Scorer ranking | General-purpose, best recall |
| `auto` | Automatically selects `fts` for short queries, `hybrid` for longer ones | Default for most use cases |

### Configuration (config.yaml)

```yaml
rag:
  fts_enabled: true
  vec_enabled: true
  search_strategy: "hybrid"  # Default strategy
  embedding_model: "BAAI/bge-small-en-v1.5"
  chunk_size: 500
  search_limit: 10
```

### Usage

```python
from rag.engine import RAGEngine

rag = RAGEngine(layer="user")

# FTS-only search (fast, keyword-based)
results = await rag.search("redis configuration", strategy="fts")

# MIB-only search (semantic similarity)
results = await rag.search("memory management patterns", strategy="mib")

# Hybrid search with Scorer (best recall)
results = await rag.search("how to configure caching", strategy="hybrid")

# Auto strategy (recommended)
results = await rag.search("redis", strategy="auto")  # Uses FTS (short query)
results = await rag.search("how to set up redis caching layer", strategy="auto")  # Uses hybrid
```

---

## Scoring Modes

The unified `Scorer` blends multiple signals into a single `final_score` for ranking results.

### Scoring Dimensions

| Dimension | Weight | Description |
|-----------|--------|-------------|
| `relevance` | 1.0 (default) | Blend of FTS5 rank + binary similarity |
| `novelty` | 0.0 (default) | ITS-inspired surprise: `-log2(prior) / log2(N)` |
| `type_boost` | 0.0 (default) | Wiki-type bonuses (error: 0.12, decision: 0.10, spec: 0.08) |

### Scoring Weights

```python
from rag.scoring import Scorer, ScoringWeights

# Default: relevance only
scorer = Scorer(mode="rrf")

# Custom weights
weights = ScoringWeights(relevance=0.7, novelty=0.2, type_boost=0.1)
scorer = Scorer(mode="rrf", weights=weights)
```

### Scoring Formula

```
final_score = w_relevance × relevance + w_novelty × novelty + w_type_boost × type_boost
```

Where:
- `relevance = (rrf_score + bin_score) / 2` (if bin_score available)
- `novelty = -log2(prior) / log2(total_retrievals)` (lower prior → higher novelty)
- `type_boost` = predefined bonus based on `wiki_type`

### Wiki-Type Boosts

| Type | Boost | Description |
|------|-------|-------------|
| `error` | 0.12 | Error patterns, debugging notes |
| `decision` | 0.10 | Architecture decisions, design choices |
| `spec` | 0.08 | Specifications, requirements |
| `code` | 0.05 | Code snippets, implementations |
| `note` | 0.02 | General notes |

---

## Binary Embeddings (MIB)

The RAG engine uses **Maximally-Informative Binarization (MIB)** for fast vector search without requiring sqlite-vec. Embeddings are binarized to 48 bytes (384 dims → 384 bits → 48 bytes) and searched using Hamming distance.

### Installation

```bash
# Binary search requires numpy
pip install mcp-ariel-memory[binary]

# Optional: ANN index for 1M+ chunks
pip install mcp-ariel-memory[ann]
```

### Configuration (config.yaml)

```yaml
binary:
  enabled: true          # Enable binary embeddings
  mode: "naive"          # naive | supervised_path
  dim: 384               # Embedding dimension
  thresholds_path: "~/.mcp-ariel-memory/thresholds.npy"  # For supervised mode
```

### How It Works

1. **Ingest**: Float32 embedding (1536 bytes) + binary embedding (48 bytes) stored in `rag_chunks`
2. **Search**: Hamming distance on binary embeddings (O(n) but ~10x faster than float32)
3. **RRF**: Combines FTS5 full-text with binary vector similarity via Reciprocal Rank Fusion

### Performance

| Chunks | Binary Search | Float32 Scan |
|--------|---------------|--------------|
| 1K | ~5ms | ~50ms |
| 10K | ~30ms | ~500ms |
| 100K | ~300ms | ~5s |

---

## Supervised Thresholds

MIB binarization supports **supervised threshold training** for better accuracy than naive sign-based binarization.

### Modes

| Mode | Description | Accuracy |
|------|-------------|----------|
| `naive` | Threshold = 0.0 (sign of embedding) | Baseline |
| `supervised_path` | Per-dimension thresholds trained on labeled data | +10-15% recall |

### Training Thresholds

```python
import numpy as np
from rag.quantize import train_supervised_thresholds

# Train on labeled query-document pairs
# queries: List[str], documents: List[str], labels: List[bool]
thresholds = train_supervised_thresholds(queries, documents, labels, dim=384)

# Save for production use
np.save("~/.mcp-ariel-memory/thresholds.npy", thresholds)
```

### Using Supervised Thresholds

```python
from rag.engine import RAGEngine

rag = RAGEngine(
    layer="user",
    binary_threshold_mode="supervised_path",
    binary_thresholds_path="~/.mcp-ariel-memory/thresholds.npy"
)

# Or pass thresholds directly
import numpy as np
thresholds = np.load("thresholds.npy")
rag = RAGEngine(layer="user", thresholds=thresholds)
```

### How Supervised Thresholds Work

1. **Training**: Learn optimal per-dimension thresholds that maximize retrieval quality
2. **Binarization**: Each dimension is binarized independently using its learned threshold
3. **Search**: Hamming distance on binarized vectors (same as naive, but with better thresholds)

### MIB Format

- **Dimensions**: 384 (configurable via `binary_dim`)
- **Storage**: 48 bytes per embedding (384 bits packed into bytes)
- **Distance**: Hamming distance (popcount of XOR)

---

## Table of Contents

- [Unified Search API](#unified-search-api)
- [Scoring Modes](#scoring-modes)
- [Binary Embeddings (MIB)](#binary-embeddings-mib)
- [Supervised Thresholds](#supervised-thresholds)
- [RAGEngine](#ragengine)
- [Strategy (Enum)](#strategy)
- [RouterResult](#routerresult)
- [RetrievalRouter](#retrievalrouter)
- [ConflictResolver](#conflictresolver)

---

## RAGEngine

`rag/engine.py` — FTS5 + binary embeddings hybrid search engine. Embeddings are computed once at ingest time and stored in `rag_chunks.embedding` (float32) and `rag_chunks.bin_embedding` (binary MIB).

### Constructor

```python
RAGEngine(
    cm: Optional[AsyncConnectionManager] = None,
    layer: str = "user",
    binary_dim: int = 384,
    binary_threshold_mode: str = "naive",
    binary_thresholds_path: Optional[str] = None,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cm` | `AsyncConnectionManager` | `None` (uses global `connection_manager`) | Database connection manager |
| `layer` | `str` | `"user"` | Memory layer (e.g., `"user"`, `"session"`) |
| `binary_dim` | `int` | `384` | Embedding dimension for binary quantization |
| `binary_threshold_mode` | `str` | `"naive"` | Binarization mode: `"naive"` (sign) or `"supervised_path"` (per-dim thresholds from file) |
| `binary_thresholds_path` | `str` | `None` | Path to `.npy` file with supervised thresholds |

```python
from rag.engine import RAGEngine

rag = RAGEngine(layer="user")
rag = RAGEngine(cm=my_cm, layer="session", binary_dim=384)
```

### `init_db()`

```python
async def init_db(self) -> None
```

Creates the `rag_pages`, `rag_chunks`, `rag_relations` tables and the `rag_fts` FTS5 virtual table (if FTS5 is available in the SQLite build). The `rag_chunks` table includes `embedding` (float32) and `bin_embedding` (binary MIB) columns.

```python
rag = RAGEngine(layer="user")
await rag.init_db()
# Tables created: rag_pages, rag_chunks, rag_relations, rag_fts (if available)
```

### `ingest_file()`

```python
async def ingest_file(self, filepath: Path, user_id: str = "default", wiki_type: str = None) -> str
```

Ingests a file from disk. Computes SHA256 hash for deduplication — files with an existing hash are skipped. Chunks the content, generates embeddings, and stores them.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `filepath` | `Path` | — | Path to the file to ingest |
| `user_id` | `str` | `"default"` | Owner user ID |
| `wiki_type` | `str` | `None` | Optional categorization tag |

**Returns**: `str` — `"[OK] filename (N chunks)"` on success, `"[SKIP] filename (already ingested)"` if duplicate.

```python
from pathlib import Path

rag = RAGEngine(layer="user")
await rag.init_db()

result = await rag.ingest_file(Path("docs/architecture.md"), user_id="alice", wiki_type="docs")
# "[OK] architecture.md (4 chunks)"

result = await rag.ingest_file(Path("docs/architecture.md"), user_id="alice")
# "[SKIP] architecture.md (already ingested)"
```

### `ingest_text()`

```python
async def ingest_text(self, title: str, text: str, user_id: str = "default",
                      wiki_type: str = None, path: str = "",
                      relation_to: int = None, relation_type: str = "elaborates") -> int
```

Ingests raw text content. SHA256 deduplication. Optionally creates a relation to an existing page.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | `str` | — | Page title |
| `text` | `str` | — | Content to ingest |
| `user_id` | `str` | `"default"` | Owner user ID |
| `wiki_type` | `str` | `None` | Optional categorization tag |
| `path` | `str` | `""` | Optional file path reference |
| `relation_to` | `int` | `None` | Target page ID to create a relation from this page |
| `relation_type` | `str` | `"elaborates"` | Relation type (default: `"elaborates"`) |

**Returns**: `int` — The page ID. Returns existing page ID if already ingested.

```python
rag = RAGEngine(layer="user")
await rag.init_db()

page_id = await rag.ingest_text("Architecture", "Two-layer memory system", user_id="alice")
# 1

page_id2 = await rag.ingest_text("Details", "Deep dive into the layers", user_id="alice", relation_to=page_id)
# 2 (also creates a relation: page_id2 -> page_id)
```

### `search()`

```python
async def search(self, query: str, user_id: str = "default", strategy: Optional[StrategyT] = None, limit: int = 10) -> List[Dict[str, Any]]
```

Unified search method with pluggable strategies. Routes to `_search_fts5()`, `_search_binary()`, or `_search_hybrid()` based on the `strategy` parameter.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | — | Search query |
| `user_id` | `str` | `"default"` | Filter by owner |
| `strategy` | `StrategyT` | `None` (uses `self.search_strategy`) | `"fts"`, `"mib"`, `"hybrid"`, or `"auto"` |
| `limit` | `int` | `10` | Maximum results |

**Returns**: `List[Dict[str, Any]]` — Each dict contains:
- `id` (int): Page ID
- `title` (str): Page title
- `content` (str): Content (truncated to 500 chars)
- `wiki_type` (str or None): Wiki category
- `score` (float): Relevance score
- `source` (str): `"fts5"`, `"like"`, `"mib"`, or `"rrf(fts+mib)"`

```python
rag = RAGEngine(layer="user")

# FTS-only search
results = await rag.search("memory architecture", strategy="fts", limit=5)
# [{"id": 1, "title": "Architecture", "content": "...", "score": 0.85, "source": "fts5"}]

# MIB-only search (semantic similarity)
results = await rag.search("caching patterns", strategy="mib", limit=5)
# [{"id": 2, "title": "Cache", "content": "...", "score": 0.82, "source": "mib"}]

# Hybrid search (best recall)
results = await rag.search("how to configure caching", strategy="hybrid", limit=5)
# [{"id": 1, "title": "Architecture", "content": "...", "score": 0.0325, "source": "rrf(fts+mib)"}]

# Auto strategy (recommended)
results = await rag.search("redis", strategy="auto", limit=5)
# Uses FTS for short queries, hybrid for longer ones
```

**Auto Strategy Logic**:
- If query has ≤2 words → uses `fts`
- Otherwise → uses `hybrid`

### `search_rrf()`

```python
async def search_rrf(self, query: str, user_id: str = "default", limit: int = 10, k: int = 60) -> List[Dict[str, Any]]
```

Reciprocal Rank Fusion (RRF) hybrid search combining FTS5 full-text and binary vector similarity scores.

**Formula**: `score = Σ 1 / (k + rank_i)` for each source (FTS5, binary). `k=60` is the standard RRF constant.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | — | Search query |
| `user_id` | `str` | `"default"` | Filter by owner |
| `limit` | `int` | `10` | Maximum results |
| `k` | `int` | `60` | RRF constant (higher = less weight on rank) |

**Returns**: `List[Dict[str, Any]]` — Each dict contains:
- `id` (int): Page ID
- `title` (str): Page title
- `content` (str): Content (truncated to 500 chars)
- `wiki_type` (str or None): Wiki category
- `score` (float): RRF fusion score
- `source` (str): `"rrf(fts+mib)"`, `"fts5"`, or `"mib"`

```python
rag = RAGEngine(layer="user")
results = await rag.search_rrf("memory architecture", user_id="alice", limit=5)
# [{"id": 1, "title": "Architecture", "content": "...", "score": 0.0325, "source": "rrf(fts+vec)"}]
```

**Fallback**: If vector search is unavailable, falls back to pure FTS5.

### `search_binary()`

```python
async def search_binary(self, query: str, user_id: str = "default", limit: int = 10) -> List[Dict[str, Any]]
```

Exhaustive linear scan over binary embeddings using Hamming distance. No sqlite-vec required. 100% recall (deterministic). ~10x faster than float32 comparison.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | — | Search query |
| `user_id` | `str` | `"default"` | Filter by owner |
| `limit` | `int` | `10` | Maximum results |

**Returns**: `List[Dict[str, Any]]` — Each dict contains:
- `id` (int): Chunk ID
- `page_id` (int): Parent page ID
- `title` (str): Page title
- `content` (str): Chunk content (truncated to 1024 chars)
- `wiki_type` (str or None): Wiki category
- `score` (float): Hamming similarity (0.0–1.0)
- `source` (str): `"mib"`

```python
rag = RAGEngine(layer="user")
results = await rag.search_binary("memory architecture", user_id="alice", limit=5)
# [{"id": 1, "page_id": 1, "title": "Architecture", "content": "...", "score": 0.85, "source": "mib"}]
```

**Performance**: On 10K chunks, binary search takes ~30ms single-threaded with numpy.

### `get_relations()`

```python
async def get_relations(self, page_id: int, depth: int = 1) -> List[Dict[str, Any]]
```

Retrieves graph relations from a page using recursive CTE traversal. Follows `rag_relations` edges up to `depth` hops.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page_id` | `int` | — | Source page ID |
| `depth` | `int` | `1` | Maximum traversal depth (hops) |

**Returns**: `List[Dict[str, Any]]` — Each dict contains:
- `id` (int): Target page ID
- `title` (str): Target page title
- `relation` (str): Relation type (e.g., `"elaborates"`)
- `weight` (float): Relation weight

```python
rag = RAGEngine(layer="user")
relations = await rag.get_relations(page_id=1, depth=1)
# [{"id": 2, "title": "Details", "relation": "elaborates", "weight": 0.8}]

relations = await rag.get_relations(page_id=1, depth=2)
# Returns relations up to 2 hops deep
```

### `add_relation()`

```python
async def add_relation(self, source_id: int, target_id: int,
                       relation_type: str = "elaborates", weight: float = 0.8) -> None
```

Creates or updates a relation between two pages. Uses `INSERT OR REPLACE` (upsert).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `source_id` | `int` | — | Source page ID |
| `target_id` | `int` | — | Target page ID |
| `relation_type` | `str` | `"elaborates"` | Relation type string |
| `weight` | `float` | `0.8` | Relation weight (0.0–1.0) |

```python
rag = RAGEngine(layer="user")
await rag.add_relation(1, 2, "depends_on", weight=0.9)
await rag.add_relation(1, 3, "elaborates")
```

### `count_pages()`

```python
async def count_pages(self, user_id: str = None) -> int
```

Counts indexed pages. Optionally filters by user.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | `None` | If provided, count only this user's pages |

**Returns**: `int` — Number of pages.

```python
rag = RAGEngine(layer="user")
total = await rag.count_pages()
# 42

alice_count = await rag.count_pages(user_id="alice")
# 15
```

### `count_chunks()`

```python
async def count_chunks(self) -> int
```

**Returns**: `int` — Total number of chunks across all pages.

```python
rag = RAGEngine(layer="user")
chunks = await rag.count_chunks()
# 168
```

### `_chunk_text()`

```python
def _chunk_text(self, text: str, max_size: int = 500, overlap: int = 100) -> List[str]
```

Splits text into chunks with sliding overlap for semantic continuity.

**Rules**:
1. Split on double newline (paragraph)
2. When accumulated buffer reaches `max_size`, flush it. Last `overlap` chars carry over to next chunk
3. Paragraphs longer than `max_size` are split by words (overlap only at paragraph boundaries)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | `str` | — | Input text to chunk |
| `max_size` | `int` | `500` | Maximum character count per chunk |
| `overlap` | `int` | `100` | Overlap between chunks (must be < max_size) |

**Returns**: `List[str]` — List of text chunks with sliding overlap.

```python
rag = RAGEngine(layer="user")
chunks = rag._chunk_text("First paragraph.\n\nSecond paragraph.\n\nThird paragraph.")
# ["First paragraph.", "Second paragraph.", "Third paragraph."]

# With overlap
chunks = rag._chunk_text("A" * 1000, max_size=500, overlap=100)
# ["A...A", "...A...A", "...A"]  # overlap between chunks
```

---

## Strategy

`rag/router.py` — Enum defining retrieval strategies.

```python
class Strategy(str, Enum):
    L1_BUFFER = "l1_buffer"    # Recent context / short-term memory
    SEMANTIC = "semantic"       # FTS5 + vector search (RRF)
    GRAPH = "graph"             # Epistemic graph (nodes, tags, relations)
    WIKI = "wiki"               # Wiki pages + relations via RRF
```

| Value | Description | When Used |
|-------|-------------|-----------|
| `L1_BUFFER` | Returns recent context from the in-memory buffer | Query is short (<60 chars) and contains recent-context keywords |
| `SEMANTIC` | FTS5 + vector RRF search | Default fallback for general queries |
| `GRAPH` | EpistemicGraph tag/type queries | Query contains graph-related keywords or extracted entities |
| `WIKI` | Wiki pages with relation expansion | Query contains documentation/config/architecture keywords |

---

## RouterResult

`rag/router.py` — Container for route decisions.

```python
class RouterResult:
    def __init__(self, strategy: Strategy, context: List[Dict[str, Any]], confidence: float)
```

| Attribute | Type | Description |
|-----------|------|-------------|
| `strategy` | `Strategy` | Which retrieval strategy was selected |
| `context` | `List[Dict[str, Any]]` | Retrieved context items (title, content, score, etc.) |
| `confidence` | `float` | Routing confidence (0.0–1.0) |

```python
from rag.router import Strategy, RouterResult

result = RouterResult(strategy=Strategy.WIKI, context=[...], confidence=0.95)
print(result.strategy)     # Strategy.WIKI
print(result.confidence)   # 0.95
print(len(result.context)) # number of context items
```

---

## RetrievalRouter

`rag/router.py` — Multi-signal query router. Analyzes the query against keyword sets and entity patterns to select the best retrieval strategy.

### Constructor

```python
RetrievalRouter(layer: str = "user", user_id: str = "default")
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `layer` | `str` | `"user"` | Memory layer |
| `user_id` | `str` | `"default"` | Owner user ID |

```python
from rag.router import RetrievalRouter

router = RetrievalRouter(user_id="alice")
router = RetrievalRouter(layer="session", user_id="bob")
```

### `route()`

```python
async def route(self, query: str, recent_context: List[Dict] = None) -> RouterResult
```

Main entry point. Routes a query through a priority cascade:

1. **L1 Buffer**: If query is short + contains recent keywords AND `recent_context` is provided → returns buffer
2. **Wiki**: If query matches wiki keywords → RRF search + relation expansion
3. **Graph (entity)**: If entities are extracted → EpistemicGraph tag query
4. **Graph (keyword)**: If query matches graph keywords → EpistemicGraph tag/type query
5. **Semantic**: Default fallback → RRF search

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | — | User query |
| `recent_context` | `List[Dict]` | `None` | Recent conversation context for L1 buffer |

**Returns**: `RouterResult`

```python
router = RetrievalRouter(user_id="alice")

# Wiki query
result = await router.route("How to configure Redis?")
# result.strategy = Strategy.WIKI
# result.context = [{"title": "...", "content": "...", "score": 0.95}]
# result.confidence = 0.95

# Graph query
result = await router.route("What error patterns did we see?")
# result.strategy = Strategy.GRAPH
# result.context = [{"title": "...", "type": "error_analysis", "tags": [...]}]

# Semantic fallback
result = await router.route("general question about the project")
# result.strategy = Strategy.SEMANTIC
# result.context = [{"id": 1, "title": "...", "score": 0.8}]

# L1 buffer
result = await router.route("как это работает", recent_context=[{"role": "assistant", "content": "..."}])
# result.strategy = Strategy.L1_BUFFER
# result.confidence = 0.9
```

### `_extract_entities()`

```python
def _extract_entities(self, query: str) -> Set[str]
```

NER-lite entity extraction using regex patterns. Matches Russian/English names, file paths, technologies, and programming languages. Entities shorter than 3 characters are filtered.

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | `str` | Input query |

**Returns**: `Set[str]` — Lowercase entity strings.

**Patterns matched**:
- `r"\b([А-ЯЁ][а-яё]+)\b"` — Russian names
- `r"\b([A-Z][a-z]+)\b"` — English names
- `r"\b(\w+)\.(py|js|ts|go|rs)\b"` — File paths
- `r"\b(redis|sqlite|postgres|mysql|mongo)\b"` — Technologies
- `r"\b(python|javascript|typescript|go|rust)\b"` — Languages

```python
router = RetrievalRouter(user_id="alice")
entities = router._extract_entities("Как настроить Redis в Python?")
# {"redis", "python"}

entities = router._extract_entities("Что думает Мария о PostgreSQL?")
# {"мария", "postgresql"}
```

### `_is_recent_query()`

```python
def _is_recent_query(self, query: str) -> bool
```

Returns `True` if the query is short (<60 chars) AND contains a recent-context keyword.

**Keywords**: `{"это", "почему", "как", "только что", "ранее"}`

```python
router = RetrievalRouter(user_id="alice")
router._is_recent_query("как это работает")
# True (short + contains "как" and "это")

router._is_recent_query("Как настроить Redis в Docker контейнере с кластеризацией?")
# False (too long, >60 chars)
```

### `_is_wiki_query()`

```python
def _is_wiki_query(self, query: str) -> bool
```

Returns `True` if the query contains any wiki/documentation keyword.

**Keywords**: `{"документация", "настроить", "архитектура", "баг", "конфиг", "функция", "класс", "модуль", "сервис", "api", "handler"}`

```python
router = RetrievalRouter(user_id="alice")
router._is_wiki_query("Как настроить Redis?")
# True (contains "настроить")

router._is_wiki_query("What's the weather?")
# False
```

### `_is_graph_query()`

```python
def _is_graph_query(self, query: str) -> bool
```

Returns `True` if the query contains any graph/relations keyword.

**Keywords**: `{"связи", "связано", "relation", "graph", "граф", "паттерн", "ошибка", "решение", "почему выбрал", "error_pattern", "decision", "learned"}`

```python
router = RetrievalRouter(user_id="alice")
router._is_graph_query("Какие связи между модулями?")
# True (contains "связи")

router._is_graph_query("What decisions did we make?")
# True (contains "decision")
```

---

## ConflictResolver

`rag/conflict.py` — Detects conflicting memory entries using keyword-based similarity.

### Constructor

```python
ConflictResolver(cm: Optional[AsyncConnectionManager] = None)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cm` | `AsyncConnectionManager` | `None` (uses global `connection_manager`) | Database connection manager |

```python
from rag.conflict import ConflictResolver

cr = ConflictResolver()
cr = ConflictResolver(cm=my_cm)
```

### `_init_db()`

```python
async def _init_db(self) -> None
```

Creates the `memory_conflicts` table and indexes. Called automatically by `check()`.

### `check()`

```python
async def check(self, user_id: str, new_content: str, min_similarity: float = 0.3) -> Dict[str, Any]
```

Checks if `new_content` conflicts with existing entries. Extracts top-5 keywords (>3 chars), runs LIKE search, then calculates word-level Jaccard similarity.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | — | Owner user ID |
| `new_content` | `str` | — | Content to check for conflicts |
| `min_similarity` | `float` | `0.3` | Minimum similarity threshold |

**Returns**: `Dict[str, Any]`:
- If no conflict: `{"content": ..., "is_conflict": False}`
- If conflict: `{"content": ..., "is_conflict": True, "conflict_group_id": "...", "conflicts_with_id": int, "similarity": float}`

```python
cr = ConflictResolver()

result = await cr.check("alice", "Python is the best language")
# {"content": "Python is the best language", "is_conflict": False}

result2 = await cr.check("alice", "Python is best for coding")
# {"content": "Python is best for coding", "is_conflict": True,
#  "conflict_group_id": "abc-123", "conflicts_with_id": 1, "similarity": 0.6}
```

### `get_conflicts()`

```python
async def get_conflicts(self, conflict_group_id: str) -> List[Dict[str, Any]]
```

Retrieves all entries in a conflict group, ordered by creation time (newest first).

| Parameter | Type | Description |
|-----------|------|-------------|
| `conflict_group_id` | `str` | UUID of the conflict group |

**Returns**: `List[Dict[str, Any]]` — Each dict contains:
- `id` (int): Entry ID
- `content` (str): Entry content
- `created_at` (str): Timestamp

```python
cr = ConflictResolver()
conflicts = await cr.get_conflicts("abc-123")
# [{"id": 2, "content": "Python is best for coding", "created_at": "2024-01-15..."},
#  {"id": 1, "content": "Python is the best language", "created_at": "2024-01-14..."}]
```

### `resolve()`

```python
async def resolve(self, conflict_group_id: str, keep_id: int) -> bool
```

Resolves a conflict by keeping one entry and deleting the rest. Clears the conflict flags on the kept entry.

| Parameter | Type | Description |
|-----------|------|-------------|
| `conflict_group_id` | `str` | UUID of the conflict group |
| `keep_id` | `int` | ID of the entry to keep |

**Returns**: `bool` — Always `True`.

```python
cr = ConflictResolver()
await cr.resolve("abc-123", keep_id=1)
# Entry 1 kept, entry 2 deleted, conflict flags cleared
```

### `_calculate_similarity()`

```python
def _calculate_similarity(self, text1: str, text2: str) -> float
```

Calculates word-level Jaccard similarity between two texts.

**Formula**: `|words1 ∩ words2| / |words1 ∪ words2|`

| Parameter | Type | Description |
|-----------|------|-------------|
| `text1` | `str` | First text |
| `text2` | `str` | Second text |

**Returns**: `float` — Similarity score (0.0–1.0).

```python
cr = ConflictResolver()
sim = cr._calculate_similarity("Python is the best", "Python is best for coding")
# 0.6 (3 shared words / 5 total unique words)
```

---

## Database Schema

### rag_pages

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment page ID |
| `layer` | TEXT | Memory layer |
| `user_id` | TEXT | Owner |
| `title` | TEXT | Page title |
| `path` | TEXT | File path (optional) |
| `content` | TEXT | Full content |
| `sha256_hash` | TEXT | Dedup hash |
| `wiki_type` | TEXT | Category tag |
| `created_at` | REAL | Unix timestamp |
| `updated_at` | REAL | Unix timestamp |

### rag_chunks

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Chunk ID |
| `page_id` | INTEGER FK | Parent page |
| `chunk_index` | INTEGER | Chunk position |
| `content` | TEXT | Chunk text |
| `embedding` | BLOB | Packed float32 vector |

### rag_relations

| Column | Type | Description |
|--------|------|-------------|
| `source_id` | INTEGER PK | Source page ID |
| `target_id` | INTEGER PK | Target page ID |
| `relation_type` | TEXT PK | Relation type |
| `weight` | REAL | Weight (default 0.8) |

### memory_conflicts

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Entry ID |
| `user_id` | TEXT | Owner |
| `content` | TEXT | Entry content |
| `is_conflict` | INTEGER | 0 or 1 |
| `conflict_group_id` | TEXT | UUID group |
| `created_at` | DATETIME | Timestamp |
