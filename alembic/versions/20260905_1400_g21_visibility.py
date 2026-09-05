"""C8 — core_memory visibility (pinned/private inject-флаги).

Revision ID: 20260905_1400_g21
Revises: 20260905_1200_g20
Create Date: 2026-09-05

visibility: 'visible' (default) | 'pinned' (всегда в inject) | 'private'
(исключается из recall/important-инъекции). S2/S16-хвосты C8.
"""

import contextlib

from alembic import op

revision: str = "20260905_1400_g21"
down_revision = "20260905_1200_g20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Каждый DDL отдельным execute — sqlite3-драйвер не ест несколько за раз.
    with contextlib.suppress(Exception):  # колонка уже добавлена (init_db для живых БД)
        op.execute("ALTER TABLE core_memory ADD COLUMN visibility TEXT NOT NULL DEFAULT 'visible'")


def downgrade() -> None:
    with contextlib.suppress(Exception):
        op.execute("ALTER TABLE core_memory DROP COLUMN visibility")
