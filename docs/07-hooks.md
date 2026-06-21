# Хуки — hooks/ (24 хука)

## HookRegistry (`hooks/registry.py`)

Центральный диспетчер хуков.

```python
from hooks.registry import HookRegistry

hr = HookRegistry()
hr.register("my_hook", lambda ctx: {"ok": True})
result = hr.fire("my_hook", "user", {"data": "value"})
hr.list_hooks()
```

## UserHooks (12 хуков)

| # | Хук | Триггер | Действие |
|---|-----|---------|----------|
| 1 | `message_received` | Новое сообщение | L1 + importance |
| 2 | `message_sent` | Ответ агента | L1 |
| 3 | `state_delta` | Изменение состояния | Эпизод → L3 |
| 4 | `consolidation` | L1满 (40+) | L1→L2→L3 |
| 5 | `emotion_trigger` | Сильные эмоции | → L3 |
| 6 | `nightly` | Cron (24ч) | Diary → L3 |
| 7 | `importance_gate` | Каждое сообщение | Фильтр шума (порог 0.3) |
| 8 | `auto_context` | Вопрос | Auto-inject RAG |
| 9 | `forgetting_ritual` | Cron (30 дней) | Архивация |
| 10 | `retrieval_router` | Поиск | Роутинг стратегий |
| 11 | `conflict_resolver` | Конфликт | Разрешение |
| 12 | `dream_buffer` | Периодически | Буфер мечтаний |

```python
from hooks.user_hooks import UserHooks

uh = UserHooks("alice")
r = uh._importance_gate({"text": "How do I configure Redis?"})
# {"importance": 0.8, "bypass": False}
```

## AgentHooks (12 хуков)

| # | Хук | Триггер | Действие |
|---|-----|---------|----------|
| 13 | `error_occurred` | Ошибка в коде | Анализ → AgentL3 |
| 14 | `decision_made` | Решение принято | Rationale → AgentL3 |
| 15 | `self_correction` | Исправление ошибки | Pattern → AgentL3 |
| 16 | `personality_shift` | Изменение поведения | Evolution → AgentL4 |
| 17 | `emotion_context` | Эмоции в контексте | Response → AgentL3 |
| 18 | `wiki_agent` | Cron (nightly) | Дневник → AgentL3 |
| 19 | `consolidation` | AgentL1满 | AgentL1→AgentL3 |
| 20 | `forgetting_ritual` | Cron (30 дней) | Архивация agent layer |
| 21 | `auto_context` | Вопрос о агенте | Авто-инжект agent RAG |
| 22 | `retrieval_router` | Поиск agent memory | Роутинг agent layer |
| 23 | `conflict_resolver` | Конфликт agent memory | Разрешение |
| 24 | `emotion` | Эмоции агента | Response → AgentL3 |

```python
from hooks.agent_hooks import AgentHooks

ah = AgentHooks("alice")
r = ah._error_occurred({"error": "NullPointerException"})
# {"action": "error_analyzed", "node_id": 5}
```

**Включение/отключение хуков (config.yaml):**
```yaml
hooks:
  user:
    message_received: true
    emotion_trigger: false  # отключить
  agent:
    error_occurred: true
```
