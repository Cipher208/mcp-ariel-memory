"""Tests for shared/connection.py — AsyncConnectionManager."""

import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def _uid():
    return uuid.uuid4().hex[:8]


def test_connection_get_creates_db():
    """get() should create a connection to a new database."""
    from shared.connection import AsyncConnectionManager

    async def t():
        cm = AsyncConnectionManager(base_dir="/tmp/test_conn")
        conn = await cm.get(f"test_{_uid()}.db")
        assert conn is not None
        cur = await conn.execute("SELECT 1")
        row = await cur.fetchone()
        assert row[0] == 1

    asyncio.run(t())


def test_connection_reuses():
    """get() should reuse existing connection."""
    from shared.connection import AsyncConnectionManager

    async def t():
        cm = AsyncConnectionManager(base_dir="/tmp/test_conn")
        name = f"reuse_{_uid()}.db"
        conn1 = await cm.get(name)
        conn2 = await cm.get(name)
        assert conn1 is conn2

    asyncio.run(t())


def test_connection_execute_and_fetch():
    """execute() + fetchone() should work end-to-end."""
    from shared.connection import AsyncConnectionManager

    async def t():
        cm = AsyncConnectionManager(base_dir="/tmp/test_conn")
        conn = await cm.get(f"fetch_{_uid()}.db")
        await conn.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER, val TEXT)")
        await conn.execute("INSERT INTO t VALUES (1, 'hello')")
        await conn.commit()
        cur = await conn.execute("SELECT val FROM t WHERE id=1")
        row = await cur.fetchone()
        assert row["val"] == "hello"

    asyncio.run(t())


def test_connection_executemany():
    """executemany() should insert multiple rows."""
    from shared.connection import AsyncConnectionManager

    async def t():
        cm = AsyncConnectionManager(base_dir="/tmp/test_conn")
        conn = await cm.get(f"many_{_uid()}.db")
        await conn.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER, val TEXT)")
        await conn.executemany("INSERT INTO t VALUES (?, ?)", [(1, "a"), (2, "b"), (3, "c")])
        await conn.commit()
        cur = await conn.execute("SELECT COUNT(*) FROM t")
        row = await cur.fetchone()
        assert row[0] == 3

    asyncio.run(t())


def test_connection_executescript():
    """executescript() should run DDL."""
    from shared.connection import AsyncConnectionManager

    async def t():
        cm = AsyncConnectionManager(base_dir="/tmp/test_conn")
        conn = await cm.get(f"script_{_uid()}.db")
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS script_test (id INTEGER);
            INSERT INTO script_test VALUES (42);
        """)
        cur = await conn.execute("SELECT id FROM script_test")
        row = await cur.fetchone()
        assert row[0] == 42

    asyncio.run(t())


def test_connection_rollback():
    """rollback() should undo uncommitted changes."""
    from shared.connection import AsyncConnectionManager

    async def t():
        cm = AsyncConnectionManager(base_dir="/tmp/test_conn")
        conn = await cm.get(f"rollback_{_uid()}.db")
        await conn.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER)")
        await conn.execute("INSERT INTO t VALUES (1)")
        await conn.rollback()
        cur = await conn.execute("SELECT COUNT(*) FROM t")
        row = await cur.fetchone()
        assert row[0] == 0

    asyncio.run(t())


def test_connection_stale_reopen():
    """Stale connection should be reopened automatically."""
    from shared.connection import AsyncConnectionManager

    async def t():
        cm = AsyncConnectionManager(base_dir="/tmp/test_conn")
        name = f"stale_{_uid()}.db"
        conn1 = await cm.get(name)
        await conn1.close()
        cm._conns.pop(name, None)
        conn2 = await cm.get(name)
        assert conn2 is not None
        cur = await conn2.execute("SELECT 1")
        row = await cur.fetchone()
        assert row[0] == 1

    asyncio.run(t())


def test_connection_execute_script():
    """execute_script() static method should work."""
    from shared.connection import AsyncConnectionManager

    async def t():
        cm = AsyncConnectionManager(base_dir="/tmp/test_conn")
        name = f"execs_{_uid()}.db"
        await cm.execute_script(
            name,
            """
            CREATE TABLE IF NOT EXISTS exec_test (id INTEGER);
            INSERT INTO exec_test VALUES (99);
        """,
        )
        conn = await cm.get(name)
        cur = await conn.execute("SELECT id FROM exec_test")
        row = await cur.fetchone()
        assert row[0] == 99

    asyncio.run(t())


def test_cursor_fetchall():
    """fetchall() should return all rows."""
    from shared.connection import AsyncConnectionManager

    async def t():
        cm = AsyncConnectionManager(base_dir="/tmp/test_conn")
        conn = await cm.get(f"fetchall_{_uid()}.db")
        await conn.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER)")
        await conn.executemany("INSERT INTO t VALUES (?)", [(1,), (2,), (3,)])
        await conn.commit()
        cur = await conn.execute("SELECT id FROM t ORDER BY id")
        rows = await cur.fetchall()
        assert len(rows) == 3
        assert [r[0] for r in rows] == [1, 2, 3]

    asyncio.run(t())
