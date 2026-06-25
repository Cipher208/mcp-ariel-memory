# Ядро памяти — core/ (async)

## ReflexEntry (`core/reflex.py`)

```python
@dataclass
class ReflexEntry:
    role: str          # "user" или "assistant"
    content: str       # текст сообщения
    tokens: int        # количество токенов
    timestamp: float   # время
```

## L1 ReflexBuffer (`core/reflex.py`)

Кольцевой буфер последних сообщений. RAM + JSON persistence.

```python
from core.reflex import ReflexBuffer
buf = ReflexBuffer(max_size=50, persist_path="reflex.json")
buf.add(role="user", content="Hello", tokens=5)
recent = buf.get_recent(5)
```

## SessionRecord (`core/session.py`)

```python
@dataclass
class SessionRecord:
    session_id: str
    user_id: str
    summary: str
    state_deltas: Dict
    topics: List[str]
    message_count: int
    started_at: float
    ended_at: float
```

## L2 SessionStore (`core/session.py`)

```python
from core.session import SessionStore
ss = SessionStore()
sid = await ss.create_session(user_id="alice")
await ss.close_session(sid, summary="Обсуждали проект")
sessions = await ss.get_recent_sessions("alice", limit=10)
```

## L3 EpisodicMemory (`core/episodic.py`)

```python
from core.episodic import EpisodicMemory
ep = EpisodicMemory()
await ep.save("alice", "Первая встреча", emotional_weight=0.8, tags=["work"])
await ep.get_episodes("alice", limit=10)
await ep.archive_old("alice", days=90)  # архивирует + удаляет
```

## CoreEntry (`core/memory.py`)

```python
@dataclass
class CoreEntry:
    entry_id: int
    user_id: str
    key: str
    value: str
    importance: float
    created_at: float
    updated_at: float
```

## L4 CoreMemory (`core/memory.py`)

### UPSERT-логика в `save()`

```python
async def save(self, user_id: str, key: str, value: str, importance: float = 0.5) -> int:
    conn = await self._cm.get("memory.db")
    cursor = await conn.execute(
        "SELECT entry_id FROM core_memory WHERE user_id=? AND key=?", (user_id, key))
    existing = await cursor.fetchone()

    if existing:
        # UPDATE — ключ уже существует
        await conn.execute(
            "UPDATE core_memory SET value=?, importance=?, updated_at=? WHERE entry_id=?",
            (value, importance, now, existing["entry_id"]))
        entry_id = existing["entry_id"]
    else:
        # INSERT — новый ключ
        cursor = await conn.execute(
            "INSERT INTO core_memory (user_id, key, value, importance, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, key, value, importance, now, now))
        entry_id = cursor.lastrowid

    await conn.commit()
    return entry_id
```

**Использование:**
```python
from core.memory import CoreMemory
cm = CoreMemory()

# UPSERT: сохранить или обновить
await cm.save("alice", "name", "Alice", importance=0.9)
await cm.save("alice", "name", "Alice Smith", importance=0.95)  # обновит

# Получить (возвращает None если не найден)
entry = await cm.get("alice", "name")

# Получить с default (никогда не None)
value = await cm.get_or_default("alice", "name", default="unknown")
```

## L2 SessionStore (`core/session.py`)

```python
from core.session import SessionStore

ss = SessionStore()
sid = await ss.create_session(user_id="alice")
await ss.close_session(sid, summary="Обсуждали проект")
sessions = await ss.get_recent_sessions("alice", limit=10)
count = await ss.count_sessions("alice")
```

## L3 EpisodicMemory (`core/episodic.py`)

```python
from core.episodic import EpisodicMemory

ep = EpisodicMemory()
eid = await ep.save("alice", "Первая встреча", emotional_weight=0.8, tags=["work"])
episodes = await ep.get_episodes("alice", limit=10)
episodes = await ep.search_by_tag("alice", "work")
await ep.archive_old("alice", days=90)
```

## L4 CoreMemory (`core/memory.py`)

```python
from core.memory import CoreMemory

cm = CoreMemory()
await cm.save("alice", "name", "Alice", importance=0.9)

# get() возвращает None если не найден
entry = await cm.get("alice", "name")

# get_or_default() никогда не возвращает None
value = await cm.get_or_default("alice", "name", default="unknown")
# "Alice" или "unknown"

results = await cm.search("alice", "Python")
await cm.delete("alice", "lang")
count = await cm.count("alice")
```

## MemoryManager (`core/__init__.py`)

```python
from core import memory_manager

user = memory_manager.user_memory("alice")
await user.remember("name", "Alice", 0.9)
results = await user.recall("name")
context = await user.get_context()  # текст для инжекта в промпт

agent = memory_manager.agent_memory("alice")
await agent.remember("approach", "YAGNI first", 0.9)
```

### get_context() — формат для инжекта в промпт

Метод `get_context()` возвращает текстовый контекст для инжекта в system prompt LLM:

```python
ctx = memory_manager.user_memory("alice").get_context()
print(ctx)
```

**Формат ответа:**
```
RECENT: user: Как настроить Redis?; assistant: Используй конфиг...
FACTS: name=Alice; primary_language=Python; company=Yandex
```

**Что входит:**
- **RECENT** — последние 5 сообщений из L1 ReflexBuffer (по 50 символов каждое)
- **FACTS** — ключевые факты из L4 CoreMemory (по 30 символов, отсортированы по важности)

**Использование в агенте:**
```python
# Получить контекст для промпта
user_ctx = memory_manager.user_memory("alice").get_context()
agent_ctx = memory_manager.agent_memory("alice").get_context()

prompt = f"""
Ты — AI-ассистент.

Пользователь:
{user_ctx}

Твоя память:
{agent_ctx}

Вопрос: {user_message}
"""
```
