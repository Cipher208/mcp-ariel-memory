# Ядро памяти — core/

## L1 ReflexBuffer (`core/reflex.py`)

Кольцевой буфер последних сообщений. Thread-safe, RAM + JSON persistence.

```python
from core.reflex import ReflexBuffer

buf = ReflexBuffer(max_size=50, persist_path="reflex.json")
buf.add(role="user", content="Hello", tokens=5)
recent = buf.get_recent(5)   # последние 5
buf.to_text(10)              # текстовое представление
buf.clear()
buf.size()
```

## L2 SessionStore (`core/session.py`)

История сессий с SQLite индексами.

```python
from core.session import SessionStore

ss = SessionStore()
sid = ss.create_session(user_id="alice")
ss.close_session(sid, summary="Обсуждали проект", topics=["project"])
sessions = ss.get_recent_sessions("alice", limit=10)
ss.get_session_summary("alice")
ss.count_sessions("alice")
```

## L3 EpisodicMemory (`core/episodic.py`)

Важные моменты с эмоциональным весом и тегами.

```python
from core.episodic import EpisodicMemory

ep = EpisodicMemory()
ep.save("alice", "Первая встреча с командой", emotional_weight=0.8, tags=["work"])
ep.get_episodes("alice", limit=10)
ep.search_by_tag("alice", "work")
ep.search("alice", "встреча")
ep.archive_old("alice", days=90)
```

## L4 CoreMemory (`core/memory.py`)

Ключ-значение хранилище фактов.

```python
from core.memory import CoreMemory

cm = CoreMemory()
cm.save("alice", "name", "Alice", importance=0.9)
cm.get("alice", "name")
cm.search("alice", "Python")
cm.get_all("alice", limit=10)
cm.delete("alice", "lang")
cm.count("alice")
```

## MemoryManager (`core/__init__.py`)

Единый менеджер для обоих слоёв.

```python
from core import memory_manager

user = memory_manager.user_memory("alice")
user.remember("name", "Alice", 0.9)
results = user.recall("name")
user.get_context()  # текст для инжекта в промпт

agent = memory_manager.agent_memory("alice")
agent.remember("approach", "YAGNI first", 0.9)

memory_manager.cleanup_all()
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
