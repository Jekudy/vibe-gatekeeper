"""offrecord_marks_unique_partial

Issue #67: duplicate delivery of a message with a non-normal policy caused
``OffrecordMarkRepo.create_for_message`` to insert a second audit row for the
same ``(chat_message_id, mark_type)`` pair. Adding a partial UNIQUE INDEX on
``(chat_message_id, mark_type) WHERE chat_message_id IS NOT NULL`` lets the
repo use ``ON CONFLICT DO NOTHING`` + SELECT fallback, making re-delivery a
true no-op (no duplicate audit rows).

Revision ID: 013
Revises: 012
Create Date: 2026-04-27
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013"
down_revision: Union[str, Sequence[str], None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Dedup guard: the T1-13 → #67 bug window may have produced duplicate
    # (chat_message_id, mark_type) rows before ON CONFLICT DO NOTHING was in place.
    # Keep the row with the smallest id for each pair; delete the rest so the
    # subsequent CREATE UNIQUE INDEX does not fail on pre-existing duplicates.
    op.execute(
        sa.text(
            """
            DELETE FROM offrecord_marks a
            USING offrecord_marks b
            WHERE a.id > b.id
              AND a.chat_message_id = b.chat_message_id
              AND a.mark_type = b.mark_type
              AND a.chat_message_id IS NOT NULL
            """
        )
    )

    op.create_index(
        "ix_offrecord_marks_chat_message_id_mark_type",
        "offrecord_marks",
        ["chat_message_id", "mark_type"],
        unique=True,
        postgresql_where=sa.text("chat_message_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_offrecord_marks_chat_message_id_mark_type",
        table_name="offrecord_marks",
    )
