# Wiki — wiki/ (FileWiki: файлы как source of truth)

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

## Методы FileWiki

```python
from wiki.file_wiki import FileWiki

uw = FileWiki(layer="user")
aw = FileWiki(layer="agent")

# Запись — создаёт .md файл + индексирует в FTS5
path = uw.add("diary", "Day 1", "Started project", tags=["work"], importance=0.7)
# → wiki/user/diary/Day_1.md

# Обновление — перезаписывает .md + переиндексирует
uw.update(path, content="Updated content", importance=0.8)

# Чтение
entry = uw.get(path)
# WikiEntry(title="Day 1", content="...", file_path="wiki/user/diary/Day_1.md")

# Поиск — FTS5 по всем .md файлам
results = uw.search("project")
# [{"title": "Day 1", "type": "diary", "file_path": "...", "score": 0.95}]

# Список
entries = uw.list_all()
entries = uw.list_by_type("diary")

# Удаление — удаляет .md + из индекса
uw.delete(path)

# Переиндексация — пересканировать все .md с диска
uw.reindex_all()

# Внешние папки — импорт .md извне
uw.sync_external(["/home/user/notes"])

# Какие типы включены
uw.get_enabled_types()  # ['diary', 'work_notes', ...]
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
