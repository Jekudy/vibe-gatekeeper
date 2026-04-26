"""add_ingestion_runs

T1-02: track live and import ingestion runs so every persisted ``telegram_updates`` /
``chat_messages`` row can be tagged by ``ingestion_run_id``. The migration creates the
table only — no rows are seeded; the live-ingestion service creates the long-running
``run_type='live'`` row at bot startup (see T1-04 ``bot/services/ingestion.py``).

Revision ID: 004
Revises: 003
Create Date: 2026-04-26
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, Sequence[str], None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_type", sa.String(length=32), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'running'"),
        ),
        sa.Column("stats_json", sa.JSON(), nullable=True),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("error_json", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "run_type IN ('live','import','dry_run','cancelled')",
            name="ck_ingestion_runs_run_type",
        ),
        sa.CheckConstraint(
            "status IN ('running','completed','failed','dry_run','cancelled')",
            name="ck_ingestion_runs_status",
        ),
    )
    op.create_index(
        "ix_ingestion_runs_run_type_started_at",
        "ingestion_runs",
        ["run_type", "started_at"],
    )
    op.create_index("ix_ingestion_runs_status", "ingestion_runs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_ingestion_runs_status", table_name="ingestion_runs")
    op.drop_index("ix_ingestion_runs_run_type_started_at", table_name="ingestion_runs")
    op.drop_table("ingestion_runs")
