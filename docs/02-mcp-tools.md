# MCP Tools — Полная справка (31 tool)

## User Layer (10 tools)

### `memory_user_remember`

Сохранить факт о пользователе в L4 CoreMemory.

**Параметры:**
| Параметр | Тип | По умолч. | Описание |
|----------|-----|-----------|----------|
| `user_id` | string | `"default"` | ID пользователя |
| `key` | string | `""` | Ключ факта (например `"name"`, `"lang"`) |
| `value` | string | `""` | Значение |
| `importance` | float | `0.5` | Важность 0.0–1.0 |

**Ответ:** `{"status": "ok", "entry_id": 42}`

```python
# Имя
await mcp.call_tool("memory_user_remember", {
    "user_id": "alice", "key": "name", "value": "Алиса", "importance": 0.9
})

# Язык программирования
await mcp.call_tool("memory_user_remember", {
    "user_id": "alice", "key": "primary_language", "value": "Python", "importance": 0.8
})

# Upsert (обновление существующего факта)
await mcp.call_tool("memory_user_remember", {
    "user_id": "alice", "key": "name", "value": "Алиса Иванова", "importance": 0.95
})
```

### `memory_user_recall`

Поиск по user memory (L3 + L4).

**Параметры:** `user_id`, `query`, `limit` (default 10)

**Ответ:** `{"results": [{"key": "name", "value": "Алиса", "importance": 0.9}], "count": 1}`

```python
result = await mcp.call_tool("memory_user_recall", {
    "user_id": "alice", "query": "name"
})
```

### `memory_user_forget`

Удалить факт из L4.

**Параметры:** `user_id`, `key`

**Ответ:** `{"deleted": true}` или `{"deleted": false}`

```python
await mcp.call_tool("memory_user_forget", {"user_id": "alice", "key": "hobby"})
```

### `memory_user_session_start`

Начать новую сессию.

**Ответ:** `{"session_id": "sess_alice_1782036546_0b6ec91f"}`

### `memory_user_session_end`

Завершить сессию с итогами.

**Параметры:** `user_id`, `session_id`, `summary`

### `memory_user_episode_save`

Сохранить важный эпизод в L3.

**Параметры:**
| Параметр | Тип | По умолч. | Описание |
|----------|-----|-----------|----------|
| `summary` | string | `""` | Описание эпизода |
| `weight` | float | `0.5` | Эмоциональный вес 0.0–1.0 |
| `tags` | list[str] | `None` | Теги |

```python
await mcp.call_tool("memory_user_episode_save", {
    "user_id": "alice", "summary": "Пользователь сообщил о смене работы",
    "weight": 0.8, "tags": ["work", "life_change"]
})
```

### `memory_user_episode_recall`

Найти эпизоды (все или по тегу).

**Параметры:** `user_id`, `tag` (опционально), `limit`

```python
result = await mcp.call_tool("memory_user_episode_recall", {
    "user_id": "alice", "tag": "work"
})
```

### `memory_user_graph_add`

Добавить узел в эпистемический граф.

**Параметры:** `content`, `node_type` (default `"fact"`), `tags`

### `memory_user_graph_query`

Запрос графа по тегу или типу.

**Параметры:** `user_id`, `tag`, `node_type`, `limit`

### `memory_user_stats`

Статистика по всем слоям user memory.

**Ответ:** `{"l1_buffer": 5, "l2_sessions": 12, "l3_episodes": 8, "l4_facts": 45, "wiki_pages": 20, "graph_nodes": 30}`

---

## Agent Layer (10 tools)

Аналогичные user tools, но для agent identity.

| Tool | Описание |
|------|----------|
| `memory_agent_remember` | Сохранить решение/ошибку/принцип |
| `memory_agent_recall` | Поиск agent memory |
| `memory_agent_forget` | Удалить agent факт |
| `memory_agent_session_start` | Начать agent сессию |
| `memory_agent_session_end` | Завершить agent сессию |
| `memory_agent_episode_save` | Сохранить agent эпизод |
| `memory_agent_episode_recall` | Найти agent эпизоды |
| `memory_agent_graph_add` | Добавить agent узел |
| `memory_agent_graph_query` | Запрос agent графа |
| `memory_agent_stats` | Статистика agent memory |

```python
await mcp.call_tool("memory_agent_remember", {
    "user_id": "alice", "key": "db_choice",
    "value": "PostgreSQL: надёжность + JSON support", "importance": 0.9
})

await mcp.call_tool("memory_agent_remember", {
    "user_id": "alice", "key": "principle_yagni",
    "value": "Don't implement features until actually needed", "importance": 0.85
})
```

---

## Auth (3 tools)

| Tool | Параметры | Ответ |
|------|-----------|-------|
| `memory_create_api_key` | `user_id`, `label` | `{"api_key": "ak_..."}` |
| `memory_revoke_api_key` | `api_key` | `{"revoked": true}` |
| `memory_list_api_keys` | — | `{"keys": [...]}` |

---

## Backup (4 tools)

| Tool | Параметры | Ответ |
|------|-----------|-------|
| `memory_backup_now` | — | `{"path": "..."}` |
| `memory_backup_list` | — | `{"backups": [...]}` |
| `memory_backup_restore` | `backup_name` | `{"restored": [...]}` |
| `memory_backup_status` | — | `{"running": true, ...}` |

---

## RRF + Saga + Middleware + Cleanup (4 tools)

### `memory_search_rrf`

Гибридный поиск через Reciprocal Rank Fusion (FTS5 + vector similarity).

**Параметры:** `query`, `user_id`, `limit`

**Ответ:** `{"results": [...], "count": 1, "method": "rrf"}`

**Источники:** `fts5`, `vec`, или `rrf(fts+vec)`

```python
result = await mcp.call_tool("memory_search_rrf", {
    "query": "Python AI", "user_id": "alice", "limit": 5
})
```

### `memory_saga_consolidate`

Запуск саги консолидации: gather → distill → promote. Автооткат при ошибке.

**Параметры:** `user_id`

### `memory_saga_backup`

Запуск саги бэкапа: copy → verify. Автооткат при ошибке.

### `memory_cleanup`

Полная очистка памяти.

**Параметры:** `user_id`, `retention_days` (default 30)

**Действия:**
| Шаг | Действие |
|-----|----------|
| Deduplicate core | Удаляет дубликаты в L4 |
| Compress episodes | Удаляет слабые эпизоды (< 0.3 weight, > 30 дней) |
| DreamBuffer cleanup | Очищает staging > 24ч или > 500 записей |
| Audit archive | Архивирует > 30 дней в JSON, удаляет из БД |
| Backup cleanup | Удаляет бэкапы старше retention_days |
| Saga cleanup | Удаляет завершённые саги > 1 часа |

```python
result = await mcp.call_tool("memory_cleanup", {
    "user_id": "alice", "retention_days": 30
})
```
