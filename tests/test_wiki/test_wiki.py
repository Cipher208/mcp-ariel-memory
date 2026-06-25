"""Tests for wiki/ module (FileWiki) — async."""
import sys
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_file_wiki_add_search():
    from wiki.file_wiki import FileWiki
    async def t():
        w = FileWiki(layer="user")
        path = await w.add("work_notes", "Test Entry 2026", "Test content here", tags=["test"])
        assert path is not None
        assert Path(path).exists()
        results = await w.search("Test Entry 2026")
        assert len(results) > 0
    asyncio.run(t())


def test_file_wiki_enabled_types():
    from wiki.file_wiki import FileWiki
    w = FileWiki(layer="user")
    types = w.get_enabled_types()
    assert len(types) > 0
    assert "diary" in types


def test_file_wiki_count():
    from wiki.file_wiki import FileWiki
    async def t():
        w = FileWiki(layer="user")
        await w.add("work_notes", "Count Test 2026", "content")
        assert await w.count() >= 1
    asyncio.run(t())
