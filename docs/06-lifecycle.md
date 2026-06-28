# Lifecycle — lifecycle/ (async)

The `lifecycle` package manages the lifecycle of memories: detecting when something is worth saving, promoting memories between layers (staging → core), and cleaning up stale data through decay, archival, and compression.

| Module | Class | Purpose |
|--------|-------|---------|
| `forgetting.py` | `ForgettingSystem` | Decay, archival, and duplicate compression |
| `emotion_trigger.py` | `EmotionTrigger` | Detects emotionally significant messages (Russian + English + emoji) |
| `consolidation.py` | `ConsolidationEngine` | Promotes memories from staging/episodes to core (L1→L2→L3→L4) |

---

## ForgettingSystem (`lifecycle/forgetting.py`)

Manages memory decay, archival, and compression. Automatically reduces importance scores over time, archives inactive low-importance entries, and removes duplicate keys.

```python
from lifecycle.forgetting import ForgettingSystem
```

### `__init__(cm=None, layer="user")`

Initialize the forgetting system.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cm` | `AsyncConnectionManager` | `None` | Database connection manager. Falls back to the global `connection_manager` singleton. |
| `layer` | `str` | `"user"` | Memory layer to operate on. |

**Example:**

```python
from lifecycle.forgetting import ForgettingSystem

# Default usage
fs = ForgettingSystem()

# Custom connection manager
from shared.connection import AsyncConnectionManager
cm = AsyncConnectionManager()
fs = ForgettingSystem(cm=cm, layer="system")
```

**Configuration values** (from `config.get_forgetting()`):

| Config key | Default | Used by |
|------------|---------|---------|
| `decay_rate` | `0.01` | `decay_importance()` |
| `archive_threshold_days` | `90` | `archive_old_entries()` |
| `archive_min_importance` | `0.3` | `archive_old_entries()` |

---

### `async decay_importance() → int`

Apply exponential decay to all memory importance scores. Uses the formula:

```
importance = max(0.01, importance × e^(-decay_rate × days_since_update))
```

**Parameters:** None

**Returns:** `int` — number of affected rows.

**Example:**

```python
from lifecycle.forgetting import ForgettingSystem

fs = ForgettingSystem()
affected = await fs.decay_importance()
print(f"Decayed {affected} entries")

# If a memory was updated 30 days ago with importance 0.8 and decay_rate=0.01:
# importance = max(0.01, 0.8 × e^(-0.01 × 30)) ≈ max(0.01, 0.8 × 0.741) ≈ 0.593
```

---

### `async archive_old_entries() → int`

Move entries older than `archive_days` with importance below `archive_min_importance` to the archive. Uses `ArchivedMemories.archive()` for persistent archival, then deletes the original rows from `core_memory`.

**Parameters:** None

**Returns:** `int` — number of archived entries.

**Example:**

```python
from lifecycle.forgetting import ForgettingSystem

fs = ForgettingSystem()
archived = await fs.archive_old_entries()
print(f"Archived {archived} entries")

# Entries older than 90 days with importance < 0.3 are archived
# Archive files are stored in ~/.mcp-ariel-memory/archives/
```

---

### `async compress_duplicates() → int`

Remove duplicate keys within the same user, keeping only the most recently updated entry for each `(user_id, key)` pair.

**Parameters:** None

**Returns:** `int` — number of removed duplicate entries.

**Example:**

```python
from lifecycle.forgetting import ForgettingSystem

fs = ForgettingSystem()
removed = await fs.compress_duplicates()
print(f"Removed {removed} duplicates")

# If user "alice" has two entries with key "favorite_color":
#   - entry_id=1, updated_at=1000
#   - entry_id=2, updated_at=2000  ← this one is kept
# The older entry (entry_id=1) is deleted.
```

---

### `async cleanup() → Dict[str, int]`

Run all forgetting operations in sequence: decay → archive → compress. This is the main entry point for periodic maintenance.

**Parameters:** None

**Returns:** `Dict[str, int]` with keys:

| Key | Description |
|-----|-------------|
| `"decayed"` | Number of entries with decayed importance |
| `"archived"` | Number of entries moved to archive |
| `"compressed"` | Number of duplicate entries removed |

**Example:**

```python
from lifecycle.forgetting import ForgettingSystem

fs = ForgettingSystem()
stats = await fs.cleanup()
print(stats)
# {"decayed": 15, "archived": 3, "compressed": 2}
```

---

## EmotionTrigger (`lifecycle/emotion_trigger.py`)

Rule-based detector that identifies emotionally significant messages. Supports Russian and English text, emoji detection, regex phrase patterns, emotional state context, and structural heuristics (long messages, multiple questions, exclamation marks).

```python
from lifecycle.emotion_trigger import EmotionTrigger
```

### Emotion Categories

| Emotion | Russian examples | English examples | Emoji |
|---------|-----------------|-----------------|-------|
| `love` | люблю, обожаю, адорю, влюблён, дорогой | love, adore, beloved, dear | ❤️ 😍 🥰 💕 |
| `fear` | боюсь, страшно, ужас, паник, тревог | afraid, scared, terrified, panic, anxiety | 😨 😱 😰 😥 |
| `anger` | ненавижу, бесит, злюсь, раздраж, гнев | hate, angry, furious, frustrated, annoyed | 😡 🤬 😤 💢 |
| `joy` | счастлив, рад, весел, отличн, прекрасн, ура, класс | happy, glad, cheerful, wonderful, amazing, awesome | 😊 🎉 😄 🥳 😁 |
| `gratitude` | спасибо, благодарю, благодарн, признателен | thanks, thank you, grateful, appreciate | — |
| `importance` | важно, критично, срочно, необходимо, запомни | important, critical, urgent, remember, never forget | — |
| `sadness` | грустно, печальн, тоск, одинок, жаль, слёзы | sad, sorrow, lonely, regret, tears | 😢 😭 😞 😔 |
| `surprise` | удивлён, неожиданн, внезапно | surprised, unexpected, suddenly, wow | 😲 🤯 😮 ❗ |

### Detection Priority

1. **Phrase patterns** (highest) — regex matches on Russian + English phrases, e.g. `я тебя люблю`, `I love you`, `никогда не забудь`
2. **Emotion markers** — keyword presence in message text
3. **Emoji markers** — emoji detection in message text
4. **Emotional state context** — `joy > 0.8` or `interest > 0.8`
5. **State shift** — any `state_delta` value with `abs(delta) > 0.15`
6. **Long message** — > 300 characters
7. **Complex question** — 3+ `?` characters
8. **Exclamation** — 2+ `!` characters

---

### `should_save(message, emotional_state=None, state_delta=None) → Tuple[bool, str, float]`

Determine if a message should trigger memory saving based on emotional content.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `message` | `str` | — | The user's message to analyze. |
| `emotional_state` | `dict` | `None` | Current emotional state with keys like `"joy"`, `"interest"` (0.0–1.0). |
| `state_delta` | `dict` | `None` | Change in emotional state, e.g. `{"joy": 0.3}`. Triggers if any delta exceeds `STATE_SHIFT_THRESHOLD` (0.15). |

**Returns:** `Tuple[bool, str, float]`

| Element | Description |
|---------|-------------|
| `bool` | Whether this message should be saved. |
| `str` | Reason code: `emotion_love`, `emotion_fear`, `emotion_anger`, `emotion_joy`, `emotion_gratitude`, `emotion_importance`, `emotion_sadness`, `emotion_surprise`, `high_emotion`, `state_shift_<key>`, `long_message`, `complex_question`, `exclamation`, or `""` if not triggered. |
| `float` | Confidence weight (0.0–1.0). |

**Examples:**

```python
from lifecycle.emotion_trigger import EmotionTrigger

et = EmotionTrigger()

# Russian emotional messages
et.should_save("я тебя люблю!")
# → (True, "emotion_love", 0.8)

et.should_save("боюсь что это плохо")
# → (True, "emotion_fear", 0.6)

et.should_save("никогда не забудь про встречу")
# → (True, "emotion_importance", 0.8)

# English emotional messages
et.should_save("I love you so much")
# → (True, "emotion_love", 0.8)

et.should_save("Thanks for the help!")
# → (True, "emotion_gratitude", 0.5)

et.should_save("This is important to remember")
# → (True, "emotion_importance", 0.7)

# Emoji detection
et.should_save("Great! 😊🎉")
# → (True, "emotion_joy", 0.5)

# Emotional state context
et.should_save("ok", emotional_state={"joy": 0.9})
# → (True, "high_emotion", 0.6)

# State shift
et.should_save("whatever", state_delta={"interest": 0.3})
# → (True, "state_shift_interest", 0.4)

# Structural triggers
et.should_save("a" * 400)       # long message → (True, "long_message", 0.3)
et.should_save("why? how? what?")  # 3 questions → (True, "complex_question", 0.4)
et.should_save("no!! really!!")   # 2 exclamations → (True, "exclamation", 0.3)

# Non-triggering message
et.should_save("ok")
# → (False, "", 0.0)
```

### Module-Level Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `STATE_SHIFT_THRESHOLD` | `0.15` | Minimum delta magnitude to trigger a state shift detection |
| `EMOTION_MARKERS` | `dict` | Keyword lists per emotion (Russian + English) |
| `PHRASE_PATTERNS` | `list` | Russian regex patterns: `(pattern, emotion, weight)` |
| `PHRASE_PATTERNS_EN` | `list` | English regex patterns: `(pattern, emotion, weight)` |
| `EMOJI_MARKERS` | `dict` | Emoji lists per emotion |

---

## ConsolidationEngine (`lifecycle/consolidation.py`)

Promotes memories between layers: staging → core (L1→L2→L3→L4). Consolidates staging items and high-emotion episodes into persistent `CoreMemory` via `CoreMemory.save()`.

```python
from lifecycle.consolidation import ConsolidationEngine
```

---

### `__init__(cm=None)`

Initialize the consolidation engine.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cm` | `AsyncConnectionManager` | `None` | Database connection manager. Falls back to global `connection_manager` singleton. |

**Example:**

```python
from lifecycle.consolidation import ConsolidationEngine

# Default
ce = ConsolidationEngine()

# Custom connection manager
from shared.connection import AsyncConnectionManager
cm = AsyncConnectionManager()
ce = ConsolidationEngine(cm=cm)
```

---

### `async consolidate_staging(user_id, staging_items, min_importance=0.7) → Dict[str, int]`

Promote staging items to core memory. Items with importance below `min_importance` are skipped. Each promoted item is saved via `CoreMemory.save()` with a key derived from its content (first 30 chars, lowered, spaces replaced with underscores, prefixed with `staging_`).

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | — | User identifier. |
| `staging_items` | `List[Dict[str, Any]]` | — | List of staging dicts. Each must have `"content"` (str) and optionally `"importance"` (float, default 0.7). |
| `min_importance` | `float` | `0.7` | Minimum importance threshold. Items below this are skipped. |

**Returns:** `Dict[str, int]`

| Key | Description |
|-----|-------------|
| `"promoted"` | Number of items promoted to core. |
| `"skipped"` | Number of items skipped (below threshold). |

**Example:**

```python
from lifecycle.consolidation import ConsolidationEngine

ce = ConsolidationEngine()

staging_items = [
    {"content": "User prefers dark mode", "importance": 0.8},
    {"content": "Discussed vacation plans", "importance": 0.9},
    {"content": "Mentioned lunch", "importance": 0.3},  # below threshold
]

result = await ce.consolidate_staging("alice", staging_items, min_importance=0.7)
print(result)
# {"promoted": 2, "skipped": 1}

# Promoted items in core_memory:
#   key="staging_user_prefers_dark_mode",  value="User prefers dark mode",  importance=0.8
#   key="staging_discussed_vacation_plan", value="Discussed vacation plans", importance=0.9
```

---

### `async consolidate_episodes(user_id, episodic_db=None, min_weight=0.7) → int`

Promote high-emotion episodes to core memory. Queries the `episodes` table for entries with `emotional_weight > min_weight`, takes the 10 most recent, and saves each as core memory with key prefixed by `ep_`.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | — | User identifier. |
| `episodic_db` | `str` | `None` | Database filename for episodes. Defaults to `"memory.db"`. |
| `min_weight` | `float` | `0.7` | Minimum `emotional_weight` threshold. |

**Returns:** `int` — number of episodes consolidated.

**Example:**

```python
from lifecycle.consolidation import ConsolidationEngine

ce = ConsolidationEngine()

# Consolidate high-emotion episodes
consolidated = await ce.consolidate_episodes("alice", min_weight=0.7)
print(f"Consolidated {consolidated} episodes")
# e.g. "Consolidated 5 episodes"

# Episodes with emotional_weight > 0.7 from the episodes table are promoted
# to core_memory with key="ep_<first_30_chars>" and the summary (max 200 chars)
```

---

### `async get_stats(user_id) → Dict[str, int]`

Get summary statistics for a user's core memory.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | `str` | — | User identifier. |

**Returns:** `Dict[str, int]`

| Key | Description |
|-----|-------------|
| `"total"` | Total number of core memory entries for this user. |
| `"high_importance"` | Number of entries with `importance > 0.7`. |
| `"low_importance"` | Number of entries with `importance < 0.3`. |

**Example:**

```python
from lifecycle.consolidation import ConsolidationEngine

ce = ConsolidationEngine()
stats = await ce.get_stats("alice")
print(stats)
# {"total": 42, "high_importance": 12, "low_importance": 5}
```

---

## Putting It All Together

Typical lifecycle flow:

```python
from lifecycle.emotion_trigger import EmotionTrigger
from lifecycle.consolidation import ConsolidationEngine
from lifecycle.forgetting import ForgettingSystem

# 1. Detect if a message is worth saving
et = EmotionTrigger()
should_save, reason, weight = et.should_save("I love you! ❤️")
# should_save=True, reason="emotion_love", weight=0.8

# 2. Save to staging, then consolidate important items
ce = ConsolidationEngine()
staging_items = [{"content": "I love you! ❤️", "importance": weight}]
result = await ce.consolidate_staging("alice", staging_items, min_importance=0.5)
# {"promoted": 1, "skipped": 0}

# 3. Check memory stats
stats = await ce.get_stats("alice")
# {"total": 43, "high_importance": 13, "low_importance": 5}

# 4. Periodic maintenance — decay, archive, compress
fs = ForgettingSystem()
cleanup_stats = await fs.cleanup()
# {"decayed": 15, "archived": 3, "compressed": 2}
```
