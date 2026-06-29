"""Tests for B7: Saga idempotent step replay."""

import pytest
from shared.saga import Saga
import shared.connection as _conn_mod


@pytest.mark.asyncio
async def test_idempotent_key_replays_from_cache(tmp_path):
    """Step with idempotency_key_fn runs only once."""
    from shared.connection import AsyncConnectionManager

    m = AsyncConnectionManager(base_dir=str(tmp_path))
    await m.execute_script(
        "memory.db",
        """
        CREATE TABLE IF NOT EXISTS saga_step_log (
            saga_id TEXT NOT NULL, step_name TEXT NOT NULL, params_hash TEXT NOT NULL,
            result_json BLOB, completed_at REAL NOT NULL,
            PRIMARY KEY (saga_id, step_name, params_hash)
        ) WITHOUT ROWID
    """,
    )
    old_cm = _conn_mod.connection_manager
    _conn_mod.connection_manager = m

    try:
        call_count = {"n": 0}

        async def expensive_writes_to_db(data):
            call_count["n"] += 1
            return {"wrote": True}

        def key_fn(data):
            return f"user:{data.get('user_id', 'default')}"

        saga = Saga("idem_test", timeout_seconds=10)
        saga.add_step("write_db", expensive_writes_to_db, idempotency_key_fn=key_fn)
        await saga.execute({"user_id": "alice"})
        assert call_count["n"] == 1

        # Reuse same saga_id — should replay from cache
        same_saga = Saga("idem_test", saga_id=saga.saga_id, timeout_seconds=10)
        same_saga.add_step("write_db", expensive_writes_to_db, idempotency_key_fn=key_fn)
        await same_saga.execute({"user_id": "alice"})
        assert call_count["n"] == 1
    finally:
        _conn_mod.connection_manager = old_cm


@pytest.mark.asyncio
async def test_no_idempotency_key_always_runs(tmp_path):
    """Without idempotency_key_fn, step always runs."""
    from shared.connection import AsyncConnectionManager

    m = AsyncConnectionManager(base_dir=str(tmp_path))
    await m.execute_script(
        "memory.db",
        """
        CREATE TABLE IF NOT EXISTS saga_step_log (
            saga_id TEXT, step_name TEXT, params_hash TEXT,
            result_json BLOB, completed_at REAL,
            PRIMARY KEY (saga_id, step_name, params_hash)
        ) WITHOUT ROWID
    """,
    )
    old_cm = _conn_mod.connection_manager
    _conn_mod.connection_manager = m

    try:
        counter = {"n": 0}

        async def step(data):
            counter["n"] += 1
            return {"ok": True}

        saga = Saga("no_idem", timeout_seconds=10)
        saga.add_step("s", step)
        await saga.execute({})
        await saga.execute({})
        assert counter["n"] == 2
    finally:
        _conn_mod.connection_manager = old_cm
