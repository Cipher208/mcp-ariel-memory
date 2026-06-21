# Граф знаний — graph/

## EpistemicGraph (`graph/epistemic.py`)

Эпистемический граф с тегами, рёбрами, поиском соседей и путей.

```python
from graph.epistemic import EpistemicGraph

g = EpistemicGraph(layer="user")
n1 = g.add_node("alice", "Prefers Python", "fact", ["fact_about_user"], 0.9)
n2 = g.add_node("alice", "Knows JavaScript", "fact", ["fact_about_user"], 0.7)
g.add_edge(n1, n2, "related_to", 0.8)

nodes = g.query_by_tag("alice", "fact_about_user")
nodes = g.query_by_type("alice", "decision_log")
neighbors = g.get_neighbors(n1, depth=2)
path = g.find_path(n1, n2, max_depth=3)
g.count_nodes("alice")
```

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
