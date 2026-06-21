# MCP Tools — Полная справка (33 tools)

## User Layer (10 tools)

### `memory_user_remember`

Сохранить факт о пользователе в L4 CoreMemory.

**Параметры:** `user_id`, `key`, `value`, `importance` (0.0-1.0)

**Ответ:** `{"status": "ok", "entry_id": 42}`

```python
await mcp.call_tool("memory_user_remember", {
    "user_id": "alice", "key": "name", "value": "Алиса", "importance": 0.9
})
```

### `memory_user_recall`

Поиск по user memory (L3 + L4).

**Параметры:** `user_id`, `query`, `limit` (default 10)

### `memory_user_forget`

Удалить факт из L4.

**Параметры:** `user_id`, `key`

### `memory_user_session_start`

Начать сессию. **Ответ:** `{"session_id": "..."}`

### `memory_user_session_end`

Завершить сессию. **Параметры:** `session_id`, `summary`

### `memory_user_episode_save`

Сохранить эпизод. **Параметры:** `summary`, `weight`, `tags`

### `memory_user_episode_recall`

Найти эпизоды. **Параметры:** `tag` (опционально), `limit`

### `memory_user_graph_add`

Добавить узел. **Параметры:** `content`, `node_type`, `tags`

### `memory_user_graph_query`

Запрос графа. **Параметры:** `tag` или `node_type`, `limit`

### `memory_user_stats`

Статистика: `{"l1_buffer": 5, "l2_sessions": 12, "l3_episodes": 8, "l4_facts": 45, "wiki_pages": 20, "graph_nodes": 30}`

---

## Agent Layer (10 tools)

Аналогичные user tools для agent identity.

| Tool | Описание |
|------|----------|
| `memory_agent_remember` | Сохранить решение/ошибку |
| `memory_agent_recall` | Поиск agent memory |
| `memory_agent_forget` | Удалить agent факт |
| `memory_agent_session_start` | Начать agent сессию |
| `memory_agent_session_end` | Завершить agent сессию |
| `memory_agent_episode_save` | Сохранить agent эпизод |
| `memory_agent_episode_recall` | Найти agent эпизоды |
| `memory_agent_graph_add` | Добавить agent узел |
| `memory_agent_graph_query` | Запрос agent графа |
| `memory_agent_stats` | Статистика agent memory |

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
| `memory_backup_status` | — | `{"running": true, "jitter_seconds": 3600, ...}` |

---

## Memory Management (6 tools)

### `memory_cleanup`

Полная очистка: дедупликация, архивация, staging, audit, backup, sagas.

**Параметры:** `user_id`, `retention_days` (default 30)

### `memory_lucidity_purge`

Экстренная очистка за N часов (при утечке данных).

**Параметры:** `user_id`, `hours` (default 24)

**Что чистит:** core_memory, episodes, staging, audit_log, graph_nodes за N часов.

```python
result = await mcp.call_tool("memory_lucidity_purge", {
    "user_id": "alice", "hours": 24
})
# {"core_memory": 15, "episodes": 8, "staging": 12, "audit": 50, "graph_nodes": 5}
```

### `memory_user_context_inject`

Сжатая сводка для инжекта в промпт (L4 top-10 + L3 top-3 + L1 recent-5 + wiki-3).

**Параметры:** `user_id`

```python
result = await mcp.call_tool("memory_user_context_inject", {"user_id": "alice"})
# {"context": "FACTS: name=Alice\nEPISODES: Met team...\nRECENT: user: Hello\nWIKI: [diary] Day 1",
#  "l4_facts_count": 10, "l3_episodes_count": 3, ...}
```

### `memory_search_rrf`

Гибридный поиск RRF (FTS5 + vector). Fallback на LIKE если FTS5 недоступен.

**Параметры:** `query`, `user_id`, `limit`

### `memory_saga_consolidate`

Сага консолидации: gather → distill → promote. Автооткат + watchdog.

### `memory_saga_backup`

Сага бэкапа: copy → verify. Автооткат + persistence.
