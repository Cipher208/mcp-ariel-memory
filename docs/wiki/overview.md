# Wiki System

## Overview

Wiki system with .md files as source of truth and FTS5 full-text search.

## Content Types

14 types: spec, decision, error, code, note, guide, reference, tutorial, faq, changelog, architecture, api, example, concept

## FileWiki

File-based wiki with external folder sync:

```python
from wiki.file_wiki import FileWiki

fw = FileWiki(layer="user")
fw.add_page(title="Architecture", content="# Architecture\n...", wiki_type="spec")
results = fw.search("architecture", limit=5)
```

## UserWiki

User-specific wiki pages:

```python
from wiki.user_wiki import UserWiki

uw = UserWiki()
await uw.add_page(user_id="u1", title="My Notes", content="...")
```

## AgentWiki

Agent identity wiki:

```python
from wiki.agent_wiki import AgentWiki

aw = AgentWiki()
await aw.add_page(title="Learning", content="...")
```
