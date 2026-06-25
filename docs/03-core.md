# Ядро памяти — core/ (async)

## AsyncConnectionManager (`shared/connection.py`)

Все модули core используют единый AsyncConnectionManager через `self._cm.get("db_name")`.

## L1 ReflexBuffer (`core/reflex.py`)

Кольцевой буфер последних сообщений. RAM + JSON. Синхронный (не требует БД).

```python
from core.reflex import ReflexBuffer

buf = ReflexBuffer(max_size=50, persist_path="reflex.json")
buf.add(role="user", content="Hello", tokens=5)
recent = buf.get_recent(5)
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
