# Wiki — wiki/ (FileWiki + UserWiki/AgentWiki with FTS5)

## FileWiki (`wiki/file_wiki.py`) — core module

.md files = source of truth + SQLite FTS5 index.

### FTS5 content-sync table

```python
# content=wiki_index, content_rowid=entry_id
# FTS5 automatically syncs with wiki_index table
conn.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS wiki_fts USING fts5(
        title, content, wiki_type, tags,
        content=wiki_index,
        content_rowid=entry_id
    )
""")
```

### content_hash (MD5) deduplication

On ingest, MD5 hash of content is computed. If a file with that hash already exists in DB — skip:

```python
content_hash = hashlib.md5(content.encode()).hexdigest()
existing = await conn.execute(
    "SELECT entry_id FROM wiki_index WHERE content_hash=?", (content_hash,)).fetchone()
if existing:
    return  # skip — already indexed
```

### Config-based type disabling

Each type can be disabled in `config.yaml`:

```python
def _get_enabled_types(self) -> List[str]:
    cfg = _get_config()
    wiki_cfg = cfg.get("wiki", {}).get(self.layer, {})
    all_types = ALL_USER_TYPES if "user" in self.layer else ALL_AGENT_TYPES
    return [t for t in all_types if wiki_cfg.get(t, True)]
```

```yaml
wiki:
  user:
    diary: true
    relationships: false  # disabled
    external_dirs: ["/home/user/notes"]
```

### FileWiki Methods

```python
from wiki.file_wiki import FileWiki
uw = FileWiki(layer="user")

# add() — creates .md + indexes (skips on MD5 match)
await uw.add("diary", "Day 1", "Content", tags=["work"])

# search() — FTS5 + content-sync
results = await uw.search("Content")

# reindex_all() — re-scan all .md from disk
await uw.reindex_all()

# sync_external() — import .md from external folders
await uw.sync_external(["/home/user/notes"])
```

## UserWiki (`wiki/user_wiki.py`) — 7 types, 590 lines

Legacy module for user wiki with FTS5. Each type is a separate category.

| Type | Description |
|-----|----------|
| `diary` | Journal |
| `relationships` | Relationships |
| `desires` | Desires |
| `aspirations` | Aspirations |
| `work_notes` | Work notes |
| `preferences` | Preferences |
| `retrospective` | Retrospective |

```python
from wiki.user_wiki import UserWiki
uw = UserWiki()
await uw.add("diary", "Day 1", "Started project", ["work"], 0.7)
results = await uw.search("project")  # FTS5 search
await uw.sync_external(["/home/user/notes"])  # import .md
```

### UserWiki — All public methods

| Method | Signature | Returns | Async |
|--------|-----------|---------|-------|
| `add` | `add(user_id: str, wiki_type: str, title: str, content: str, tags: List[str] = None, importance: float = 0.5, source: str = "manual")` | `int` (entry_id) | yes |
| `update` | `update(entry_id: int, title: str = None, content: str = None, tags: List[str] = None, importance: float = None)` | `None` | yes |
| `get` | `get(entry_id: int)` | `Optional[WikiEntry]` | yes |
| `search` | `search(user_id: str, query: str, limit: int = 10)` | `List[Dict[str, Any]]` | yes |
| `list_by_type` | `list_by_type(user_id: str, wiki_type: str, limit: int = 20)` | `List[WikiEntry]` | yes |
| `list_all` | `list_all(user_id: str, limit: int = 50)` | `List[WikiEntry]` | yes |
| `delete` | `delete(entry_id: int)` | `bool` | yes |
| `count` | `count(user_id: str = None, wiki_type: str = None)` | `int` | yes |
| `get_enabled_types` | `get_enabled_types()` | `List[str]` | no |
| `get_external_dirs` | `get_external_dirs()` | `List[str]` | no |
| `sync_external` | `sync_external(user_id: str)` | `Dict[str, int]` | yes |

**WikiEntry dataclass:** `entry_id: int, user_id: str, wiki_type: str, title: str, content: str, tags: List[str], importance: float, created_at: float, updated_at: float`

## AgentWiki (`wiki/agent_wiki.py`) — 7 types, 590 lines

Legacy module for agent wiki. Lore, references, decision journal.

| Type | Description |
|-----|----------|
| `decision_log` | Decision journal |
| `error_analysis` | Error analysis |
| `personality_evolution` | Personality evolution |
| `emotional_context` | Emotional context |
| `wiki_agent` | Lore, references |
| `learning_journal` | Learning journal |
| `principle_log` | Principle journal |

```python
from wiki.agent_wiki import AgentWiki
aw = AgentWiki()
await aw.add("decision_log", "DB Choice", "SQLite for simplicity", ["tech"], 0.8)
results = await aw.search("SQLite")
await aw.sync_external(["/path/to/lore"])
```

### AgentWiki — All public methods

| Method | Signature | Returns | Async |
|--------|-----------|---------|-------|
| `add` | `add(user_id: str, wiki_type: str, title: str, content: str, tags: List[str] = None, importance: float = 0.5, source: str = "manual")` | `int` (entry_id) | yes |
| `update` | `update(entry_id: int, title: str = None, content: str = None, tags: List[str] = None, importance: float = None)` | `None` | yes |
| `get` | `get(entry_id: int)` | `Optional[AgentWikiEntry]` | yes |
| `search` | `search(user_id: str, query: str, limit: int = 10)` | `List[Dict[str, Any]]` | yes |
| `list_by_type` | `list_by_type(user_id: str, wiki_type: str, limit: int = 20)` | `List[AgentWikiEntry]` | yes |
| `list_all` | `list_all(user_id: str, limit: int = 50)` | `List[AgentWikiEntry]` | yes |
| `delete` | `delete(entry_id: int)` | `bool` | yes |
| `count` | `count(user_id: str = None, wiki_type: str = None)` | `int` | yes |
| `get_enabled_types` | `get_enabled_types()` | `List[str]` | no |
| `get_external_dirs` | `get_external_dirs()` | `List[str]` | no |
| `sync_external` | `sync_external(user_id: str)` | `Dict[str, int]` | yes |

**AgentWikiEntry dataclass:** `entry_id: int, user_id: str, wiki_type: str, title: str, content: str, tags: List[str], importance: float, created_at: float, updated_at: float`

**FTS5 indexes:** `user_wiki_fts`, `agent_wiki_fts` — full-text search.

### _parse_md() — YAML frontmatter + fallback

File is parsed with YAML frontmatter. If no frontmatter — fallback to `# Title`:

```python
def _parse_md(self, text: str) -> Dict[str, Any]:
    result = {"title": "", "content": text, "tags": [], "importance": 0.5}
    if text.startswith("---"):
        # YAML frontmatter: title, tags, importance
        ...
    if not result["title"]:
        for line in result["content"].split("\n"):
            if line.startswith("# "):
                result["title"] = line[2:].strip()
                break
    return result
```

## Architecture

`.md` files on disk = foundation. SQLite (`wiki_index.db`) = FTS5 index for search.

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

wiki_index.db                      ← FTS5 index (automatic)
```

## .md file format

```markdown
---
title: "Meeting Notes"
tags: work, important
importance: 0.7
updated: 2026-06-21T22:00:00
---

# Meeting Notes

Discussed the plan for the week.
```

## FileWiki Methods (async)

```python
from wiki.file_wiki import FileWiki

uw = FileWiki(layer="user")
aw = FileWiki(layer="agent")

# Write
path = await uw.add("diary", "Day 1", "Started project", tags=["work"], importance=0.7)

# Update
await uw.update(path, content="Updated content", importance=0.8)

# Read
entry = await uw.get(path)

# Search (FTS5)
results = await uw.search("project")

# List
entries = await uw.list_all()
entries = await uw.list_by_type("diary")

# Delete
await uw.delete(path)

# Reindex
await uw.reindex_all()

# External folders
await uw.sync_external(["/home/user/notes"])
```

### FileWiki — All public methods

| Method | Signature | Returns | Async |
|--------|-----------|---------|-------|
| `add` | `add(wiki_type: str, title: str, content: str, tags: List[str] = None, importance: float = 0.5)` | `str` (file path) | yes |
| `update` | `update(file_path: str, title: str = None, content: str = None, tags: List[str] = None, importance: float = None)` | `None` | yes |
| `get` | `get(file_path: str)` | `Optional[WikiEntry]` | yes |
| `search` | `search(query: str, limit: int = 10)` | `List[Dict[str, Any]]` | yes |
| `list_by_type` | `list_by_type(wiki_type: str, limit: int = 20)` | `List[WikiEntry]` | yes |
| `list_all` | `list_all(limit: int = 50)` | `List[WikiEntry]` | yes |
| `delete` | `delete(file_path: str)` | `bool` | yes |
| `count` | `count(wiki_type: str = None)` | `int` | yes |
| `get_enabled_types` | `get_enabled_types()` | `List[str]` | no |
| `get_external_dirs` | `get_external_dirs()` | `List[str]` | no |
| `reindex_all` | `reindex_all()` | `Dict[str, int]` | yes |
| `sync_external` | `sync_external(external_dirs: List[str] = None)` | `Dict[str, int]` | yes |

**FileWiki WikiEntry dataclass:** `entry_id: int, wiki_type: str, title: str, content: str, file_path: str, tags: List[str], importance: float, created_at: float, updated_at: float`

Note: FileWiki uses `file_path` (str) as entry identifier, unlike UserWiki/AgentWiki which use `entry_id` (int).

## Wiki types

### User (7 types)

| Type | Description |
|-----|----------|
| `diary` | Journal |
| `relationships` | Relationships |
| `desires` | Desires |
| `aspirations` | Aspirations |
| `work_notes` | Work notes |
| `preferences` | Preferences |
| `retrospective` | Retrospective |

### Agent (7 types)

| Type | Description |
|-----|----------|
| `decision_log` | Decision journal |
| `error_analysis` | Error analysis |
| `personality_evolution` | Personality evolution |
| `emotional_context` | Emotional context |
| `wiki_agent` | Lore, references |
| `learning_journal` | Learning journal |
| `principle_log` | Principle journal |

## External folders (config.yaml)

```yaml
wiki:
  user:
    diary: true
    relationships: false  # disabled
    external_dirs:
      - "/home/user/notes"
      - "C:\Users\me\journal"
  agent:
    wiki_agent: true
    external_dirs:
      - "/path/to/lore"
      - "/path/to/knowledge-base"
```

## File mapping

| File/folder | Type |
|------------|-----|
| `lore/world.md` | `wiki_agent` |
| `knowledge/python.md` | `wiki_agent` |
| `style-guide/tone.md` | `personality_evolution` |
| `errors/auth-bug.md` | `error_analysis` |
| `decisions/db-choice.md` | `decision_log` |
| `principles/testing.md` | `principle_log` |

## Benefits

- **Git-friendly** — .md files can be committed
- **Human-readable** — open in Obsidian, VS Code
- **No data loss** — on DB corruption, .md files remain intact
- **External tools** — Obsidian, Logseq, etc. can edit
