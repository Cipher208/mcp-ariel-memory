"""G2.2 — S1 order_key + S6 L0-тиры (warm tier/text_z, cold archive).

Revision ID: 20260905_1500_g22
Revises: 20260905_1400_g21
Create Date: 2026-09-05

order_key — hex-fractional индекс записи в l0_journal (midpoint между
соседями, CC0-паттерн). tier/text_z — S6 тёплый тир: tier='warm',
полный текст в zlib text_z, text = extractive-превью. l0_cold_archive —
S6 холодный тир: plaintext-полный текст, мета + decisions (CLACK-архив).
"""

import contextlib

from alembic import op

revision: str = "20260905_1500_g22"
down_revision = "20260905_1400_g21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Каждый DDL отдельным execute — sqlite3-драйвер не ест несколько за раз.
    for ddl in (
        "ALTER TABLE l0_journal ADD COLUMN order_key TEXT",
        "ALTER TABLE l0_journal ADD COLUMN tier TEXT",
        "ALTER TABLE l0_journal ADD COLUMN text_z BLOB",
    ):
        with contextlib.suppress(Exception):  # колонка уже добавлена (init_db для живых БД)
            op.execute(ddl)
    op.execute("""
    CREATE TABLE IF NOT EXISTS l0_cold_archive (
        id INTEGER PRIMARY KEY,
        ts REAL NOT NULL,
        event TEXT NOT NULL,
        raw_type TEXT NOT NULL DEFAULT 'plain',
        layer TEXT NOT NULL DEFAULT 'user',
        user_id TEXT NOT NULL DEFAULT 'default',
        decisions TEXT NOT NULL DEFAULT '[]',
        archived_at REAL NOT NULL,
        text TEXT NOT NULL
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_cold_ts ON l0_cold_archive(ts)")


def downgrade() -> None:
    with contextlib.suppress(Exception):
        op.execute("DROP TABLE IF EXISTS l0_cold_archive")
    for ddl in (
        "ALTER TABLE l0_journal DROP COLUMN text_z",
        "ALTER TABLE l0_journal DROP COLUMN tier",
        "ALTER TABLE l0_journal DROP COLUMN order_key",
    ):
        with contextlib.suppress(Exception):
            op.execute(ddl)
