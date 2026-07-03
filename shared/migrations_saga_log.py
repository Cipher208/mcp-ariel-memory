"""Migration: saga_step_log table for idempotent step replay."""


async def up(conn) -> None:
    """Create saga_step_log table."""
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS saga_step_log (
            saga_id     TEXT NOT NULL,
            step_name   TEXT NOT NULL,
            params_hash TEXT NOT NULL,
            result_json BLOB,
            completed_at REAL NOT NULL,
            PRIMARY KEY (saga_id, step_name, params_hash)
        ) WITHOUT ROWID
    """)
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_saga_step_log_lookup ON saga_step_log(saga_id)")
