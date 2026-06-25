# Граф знаний — graph/ (async, layer-aware)

## EpistemicGraph (`graph/epistemic.py`)

Layer-aware эпистемический граф с CTE WITH RECURSIVE для BFS-обхода в SQLite.

```python
from graph.epistemic import EpistemicGraph

g = EpistemicGraph(layer="user")
n1 = await g.add_node("alice", "Prefers Python", "fact", ["fact_about_user"], 0.9)
n2 = await g.add_node("alice", "Knows JavaScript", "fact", ["fact_about_user"], 0.7)
await g.add_edge(n1, n2, "related_to", 0.8)

nodes = await g.query_by_tag("alice", "fact_about_user")
count = await g.count_nodes("alice")
```

### get_neighbors() — BFS через CTE WITH RECURSIVE

Находит всех соседей на глубину `depth` без внешних БД. Рекурсивный CTE работает в SQLite:

```python
neighbors = await g.get_neighbors(n1, depth=2)
# [{"id": 2, "content": "Knows JS", "type": "fact", "relation": "related_to", "weight": 0.8}]
```

**SQL (рекурсивный CTE):**
```sql
WITH RECURSIVE graph AS (
    SELECT e.source_id, e.target_id, e.relation, e.weight, 1 as d
    FROM epi_edges e WHERE e.source_id = ?
    UNION ALL
    SELECT e.source_id, e.target_id, e.relation, e.weight, g.d + 1
    FROM epi_edges e JOIN graph g ON e.source_id = g.target_id WHERE g.d < ?
)
SELECT n.node_id, n.content, n.node_type, n.tags, g.relation, g.weight
FROM graph g JOIN epi_nodes n ON g.target_id = n.node_id WHERE n.layer = ?
```

### find_path() — поиск пути между узлами

```python
path = await g.find_path(n1, n2, max_depth=3)
# [{"target": 2, "relation": "related_to", "weight": 0.8, "depth": 1}]
```

**max_depth** берётся из `config.graph.max_depth` (default 3), переопределяется параметром.

### Теги

| User | Agent |
|------|-------|
| `fact_about_user` | `learned_from` |
| `user_decision` | `decided_because` |
| `user_preference` | `evolved_to` |
| `user_emotion` | `felt_in_context` |
| | `wiki_contains` |
| | `error_pattern` |
| | `correction_pattern` |
| | `personality_trait` |

### find_path — config vs code

`max_depth` по умолчанию берётся из `config.graph.max_depth` (default: 3). Можно переопределить через параметр:

```python
g.find_path(n1, n2)           # max_depth из config (3)
g.find_path(n1, n2, max_depth=5)  # override
```

### Теги User Layer

| Тег | Описание |
|-----|----------|
| `fact_about_user` | Факт о пользователе |
| `user_decision` | Решение пользователя |
| `user_preference` | Предпочтение пользователя |
| `user_emotion` | Эмоция пользователя |

### Теги Agent Layer

| Тег | Описание |
|-----|----------|
| `learned_from` | Агент узнал из ошибки |
| `decided_because` | Агент принял решение |
| `evolved_to` | Личность изменилась |
| `felt_in_context` | Эмоция в контексте |
| `wiki_contains` | Вторая кора мозга |
| `error_pattern` | Паттерн ошибки |
| `correction_pattern` | Паттерн исправления |
| `personality_trait` | Черта личности |

### Примеры использования тегов

```python
from graph.epistemic import EpistemicGraph

# User layer — добавить факт с тегом
g = EpistemicGraph(layer="user")
g.add_node("alice", "Prefers Python over JavaScript", "fact", ["fact_about_user", "user_preference"], 0.9)

# Запрос по тегу — все факты о пользователе
nodes = g.query_by_tag("alice", "fact_about_user")
# [{"id": 1, "content": "Prefers Python...", "type": "fact", "tags": ["fact_about_user", "user_preference"]}]

# Запрос по типу — все решения
nodes = g.query_by_type("alice", "decision")
# [{"id": 2, "content": "Chose SQLite", "type": "decision", "tags": ["user_decision"]}]

# Agent layer — ошибки и исправления
g_agent = EpistemicGraph(layer="agent")
g_agent.add_node("alice", "NPE in auth middleware", "error_analysis", ["error_pattern"], 0.8)
g_agent.add_node("alice", "Added null check", "correction", ["correction_pattern"], 0.7)

# Найти все паттерны ошибок
errors = g_agent.query_by_tag("alice", "error_pattern")
# [{"id": 1, "content": "NPE in auth middleware", "tags": ["error_pattern"]}]

# Найти все исправления
fixes = g_agent.query_by_tag("alice", "correction_pattern")
# [{"id": 2, "content": "Added null check", "tags": ["correction_pattern"]}]

# Найти путь от ошибки к исправлению
path = g_agent.find_path(1, 2)
# [{"target": 2, "relation": "corrected_by", "depth": 1}]
```

## TemporalGraph (`graph/temporal.py`)

Временной граф: события, таймлайн, каузальные цепочки.

```python
from graph.temporal import TemporalGraph

tg = TemporalGraph()
e1 = tg.add_event("alice", "message", "I need help", importance=0.6)
e2 = tg.add_event("alice", "response", "Here's how", importance=0.5)
tg.link_events(e1, e2, "follows")

timeline = tg.get_timeline("alice", limit=50)
near = tg.get_events_near("alice", timestamp=time.time(), window_seconds=3600)
chain = tg.get_causal_chain(e1, direction="forward", limit=10)
tg.count_events("alice")
```
