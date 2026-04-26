"""add_feature_flags

T1-01: persistent rollout flags for memory surfaces. All memory.* flags default OFF;
the migration does NOT seed any flag rows. Operators enable flags explicitly via the
admin UI (later phase) or via SQL.

Revision ID: 003
Revises: 002
Create Date: 2026-04-26
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, Sequence[str], None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feature_flags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("flag_key", sa.String(length=255), nullable=False),
        sa.Column("scope_type", sa.String(length=64), nullable=True),
        sa.Column("scope_id", sa.String(length=255), nullable=True),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        # Logical uniqueness: (flag_key, scope_type, scope_id). Postgres unique constraints
        # treat NULLs as distinct, which is exactly what we want — global scope (both NULL)
        # is one unique row, and per-scope rows can coexist alongside.
        sa.UniqueConstraint(
            "flag_key", "scope_type", "scope_id", name="uq_feature_flags_key_scope"
        ),
    )
    op.create_index("ix_feature_flags_enabled", "feature_flags", ["enabled"])


def downgrade() -> None:
    op.drop_index("ix_feature_flags_enabled", table_name="feature_flags")
    op.drop_table("feature_flags")
