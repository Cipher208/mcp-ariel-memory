# Wiki — wiki/ (FileWiki + UserWiki/AgentWiki с FTS5)

## FileWiki (`wiki/file_wiki.py`) — основной модуль

.md файлы = source of truth + SQLite FTS5 индекс.

```python
from wiki.file_wiki import FileWiki
uw = FileWiki(layer="user")
await uw.add("diary", "Day 1", "Content", tags=["work"])
results = await uw.search("Content")
```

## UserWiki (`wiki/user_wiki.py`) — 7 типов, 590 строк

Старый модуль для user wiki с FTS5. Каждый тип — отдельная категория.

| Тип | Описание |
|-----|----------|
| `diary` | Дневник |
| `relationships` | Отношения |
| `desires` | Желания |
| `aspirations` | Стремления |
| `work_notes` | Записи о работе |
| `preferences` | Предпочтения |
| `retrospective` | Ретроспектива |

```python
from wiki.user_wiki import UserWiki
uw = UserWiki()
await uw.add("diary", "Day 1", "Started project", ["work"], 0.7)
results = await uw.search("project")  # FTS5 поиск
await uw.sync_external(["/home/user/notes"])  # импорт .md
```

## AgentWiki (`wiki/agent_wiki.py`) — 7 типов, 590 строк

Старый модуль для agent wiki. Лор, справочники, журнал решений.

| Тип | Описание |
|-----|----------|
| `decision_log` | Журнал решений |
| `error_analysis` | Анализ ошибок |
| `personality_evolution` | Эволюция личности |
| `emotional_context` | Эмоциональный контекст |
| `wiki_agent` | Лор, справочники |
| `learning_journal` | Журнал обучения |
| `principle_log` | Журнал принципов |

```python
from wiki.agent_wiki import AgentWiki
aw = AgentWiki()
await aw.add("decision_log", "DB Choice", "SQLite for simplicity", ["tech"], 0.8)
results = await aw.search("SQLite")
await aw.sync_external(["/path/to/lore"])
```

**FTS5 индексы:** `user_wiki_fts`, `agent_wiki_fts` — полнотекстовый поиск.

## Архитектура

`.md` файлы на диске = основа. SQLite (`wiki_index.db`) = FTS5 индекс для поиска.

```
wiki/
├── user/
│   ├── diary/
│   │   ├── 2026-06-21.md         ← YAML frontmatter
│   │   └── Meeting_Notes.md
│   ├── work_notes/
│   │   └── Project_Alpha.md
│   └── preferences/
│       └── Tech_Stack.md
└── agent/
    ├── decision_log/
    │   └── DB_Choose.md
    ├── wiki_agent/
    │   ├── Lore.md
    │   └── Knowledge_Base.md
    └── principle_log/
        └── Testing.md

wiki_index.db                      ← FTS5 индекс (автоматический)
```

## Формат .md файлов

```markdown
---
title: "Meeting Notes"
tags: work, important
importance: 0.7
updated: 2026-06-21T22:00:00
---

# Meeting Notes

Обсудили план на неделю.
```

## Методы FileWiki (async)

```python
from wiki.file_wiki import FileWiki

uw = FileWiki(layer="user")
aw = FileWiki(layer="agent")

# Запись
path = await uw.add("diary", "Day 1", "Started project", tags=["work"], importance=0.7)

# Обновление
await uw.update(path, content="Updated content", importance=0.8)

# Чтение
entry = await uw.get(path)

# Поиск (FTS5)
results = await uw.search("project")

# Список
entries = await uw.list_all()
entries = await uw.list_by_type("diary")

# Удаление
await uw.delete(path)

# Переиндексация
await uw.reindex_all()

# Внешние папки
await uw.sync_external(["/home/user/notes"])
```

## Типы wiki

### User (7 типов)

| Тип | Описание |
|-----|----------|
| `diary` | Дневник |
| `relationships` | Отношения |
| `desires` | Желания |
| `aspirations` | Стремления |
| `work_notes` | Записи о работе |
| `preferences` | Предпочтения |
| `retrospective` | Ретроспектива |

### Agent (7 типов)

| Тип | Описание |
|-----|----------|
| `decision_log` | Журнал решений |
| `error_analysis` | Анализ ошибок |
| `personality_evolution` | Эволюция личности |
| `emotional_context` | Эмоциональный контекст |
| `wiki_agent` | Лор, справочники |
| `learning_journal` | Журнал обучения |
| `principle_log` | Журнал принципов |

## Внешние папки (config.yaml)

```yaml
wiki:
  user:
    diary: true
    relationships: false  # отключено
    external_dirs:
      - "/home/user/notes"
      - "C:\Users\me\journal"
  agent:
    wiki_agent: true
    external_dirs:
      - "/path/to/lore"
      - "/path/to/knowledge-base"
```

## Маппинг файлов

| Файл/папка | Тип |
|------------|-----|
| `lore/world.md` | `wiki_agent` |
| `knowledge/python.md` | `wiki_agent` |
| `style-guide/tone.md` | `personality_evolution` |
| `errors/auth-bug.md` | `error_analysis` |
| `decisions/db-choice.md` | `decision_log` |
| `principles/testing.md` | `principle_log` |

## Преимущества

- **Git-friendly** — .md файлы можно коммитить
- **Человекочитаемо** — откроешь в Obsidian, VS Code
- **Нет потери данных** — при повреждении DB, .md файлы на месте
- **Внешние инструменты** — Obsidian, Logseq и т.д. могут редактировать
