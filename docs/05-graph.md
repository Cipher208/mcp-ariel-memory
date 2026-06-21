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
