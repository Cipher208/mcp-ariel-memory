"""Tests for shared/read_only.py — full coverage."""

import sqlite3
import time
import pytest
from pathlib import Path
from shared.read_only import ReadOnlyReplica


def _create_source_db(path):
    """Helper to create a source database with test data."""
    path.mkdir(parents=True, exist_ok=True)
    db = path / "memory.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
    conn.execute("INSERT INTO test VALUES (1, 'alice')")
    conn.execute("INSERT INTO test VALUES (2, 'bob')")
    conn.commit()
    conn.close()
    return db


def test_sync_creates_replica(tmp_path):
    """sync should create a replica database."""
    src = tmp_path / "source"
    _create_source_db(src)

    replica = ReadOnlyReplica(source_dir=str(src), replica_dir=str(tmp_path / "replica"))
    result = replica.sync()
    assert result.get("memory.db") == 1
    assert (tmp_path / "replica" / "memory.db").exists()


def test_sync_returns_empty_when_no_source(tmp_path):
    """sync should return empty when source doesn't exist."""
    replica = ReadOnlyReplica(source_dir=str(tmp_path / "nonexistent"), replica_dir=str(tmp_path / "replica"))
    result = replica.sync()
    assert result == {}


def test_get_conn_returns_readonly(tmp_path):
    """get_conn should return a read-only connection."""
    src = tmp_path / "source"
    _create_source_db(src)

    replica = ReadOnlyReplica(source_dir=str(src), replica_dir=str(tmp_path / "replica"))
    replica.sync()

    conn = replica.get_conn()
    assert conn is not None
    # Should be able to read
    cur = conn.execute("SELECT * FROM test")
    rows = cur.fetchall()
    assert len(rows) == 2


def test_get_conn_falls_back_to_source(tmp_path):
    """get_conn should fall back to source if replica doesn't exist."""
    src = tmp_path / "source"
    _create_source_db(src)

    replica = ReadOnlyReplica(source_dir=str(src), replica_dir=str(tmp_path / "replica"))
    # Don't sync — replica doesn't exist

    conn = replica.get_conn()
    assert conn is not None
    cur = conn.execute("SELECT * FROM test")
    rows = cur.fetchall()
    assert len(rows) == 2


def test_is_ready_false_when_no_replica(tmp_path):
    """is_ready should return False when replica doesn't exist."""
    replica = ReadOnlyReplica(source_dir=str(tmp_path / "source"), replica_dir=str(tmp_path / "replica"))
    assert replica.is_ready() is False


def test_is_ready_true_after_sync(tmp_path):
    """is_ready should return True after sync."""
    src = tmp_path / "source"
    _create_source_db(src)

    replica = ReadOnlyReplica(source_dir=str(src), replica_dir=str(tmp_path / "replica"))
    replica.sync()
    assert replica.is_ready() is True


def test_start_stop_auto_sync(tmp_path):
    """start_auto_sync/stop should manage the background thread."""
    src = tmp_path / "source"
    _create_source_db(src)

    replica = ReadOnlyReplica(source_dir=str(src), replica_dir=str(tmp_path / "replica"))
    replica.start_auto_sync(interval_seconds=1)
    assert replica._running is True
    assert replica._thread is not None

    replica.stop()
    assert replica._running is False


def test_start_auto_sync_idempotent(tmp_path):
    """start_auto_sync should not create multiple threads."""
    src = tmp_path / "source"
    _create_source_db(src)

    replica = ReadOnlyReplica(source_dir=str(src), replica_dir=str(tmp_path / "replica"))
    replica.start_auto_sync(interval_seconds=1)
    thread1 = replica._thread
    replica.start_auto_sync(interval_seconds=1)
    thread2 = replica._thread
    assert thread1 is thread2

    replica.stop()


def test_sync_updates_last_sync_time(tmp_path):
    """sync should update _last_sync timestamp."""
    src = tmp_path / "source"
    _create_source_db(src)

    replica = ReadOnlyReplica(source_dir=str(src), replica_dir=str(tmp_path / "replica"))
    assert replica._last_sync == 0.0
    replica.sync()
    assert replica._last_sync > 0.0
