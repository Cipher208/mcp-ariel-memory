# Memory Layers

## L1: ReflexBuffer

Ring buffer for recent messages. When full, oldest entries are evicted.

```python
from core.reflex import ReflexBuffer

buf = ReflexBuffer(max_size=50)
buf.add(role="user", content="Hello", tokens=5)
recent = buf.get_recent(10)  # last 10 entries
```

**Properties** (verified by Hypothesis):

- Size never exceeds `max_size`
- FIFO eviction (oldest first)
- Thread-safe (threading.Lock)
- Concurrent add/get without crashes

## L2: EpisodicMemory

Session-level summaries. Each session gets a compressed summary.

```python
from core.episodic import EpisodicMemory

ep = EpisodicMemory()
await ep.create_session(user_id="u1", summary="Discussed architecture")
sessions = await ep.get_sessions(user_id="u1", limit=10)
```

## L3: SessionStore

Individual conversation entries with metadata.

```python
from core.session import SessionStore

ss = SessionStore()
await ss.add_entry(user_id="u1", role="user", content="Hello", tokens=5)
entries = await ss.get_entries(user_id="u1", limit=20)
```

## L4: CoreMemory

Long-term key-value store for important facts. Typed memory with per-type retention.

```python
from core.memory import CoreMemory

cm = CoreMemory()
await cm.store(user_id="u1", key="preference", value="dark mode", kind="preference")
fact = await cm.retrieve(user_id="u1", key="preference")
```

## Typed Memory

13 memory categories with different retention policies:

| Kind | Decay | Archive | Example |
|------|-------|---------|---------|
| instruction | never | never | "Always use dark mode" |
| rule | never | never | "Never deploy on Fridays" |
| commitment | never | never | "I'll finish by Friday" |
| fact | exponential | old + low importance | "User likes Python" |
| preference | slow | rarely | "Dark mode preferred" |
| decision | moderate | moderate | "Chose PostgreSQL over MySQL" |
| goal | moderate | when expired | "Deploy v2.0 by Q3" |
| observation | fast | quickly | "Server load was high" |
| relationship | slow | rarely | "Alice works with Bob" |
| question | fast | quickly | "How does X work?" |
| hypothesis | moderate | moderate | "Maybe Y causes Z" |
| context | fast | quickly | "Working on auth module" |
| todo | moderate | when done | "Fix the login bug" |
