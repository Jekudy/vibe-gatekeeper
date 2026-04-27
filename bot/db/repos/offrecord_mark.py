"""Repository for ``offrecord_marks`` (T1-13).

Thin data-access layer. The chat_messages handler (T1-12 wiring) calls
``create_for_message`` whenever ``detect_policy`` returns non-normal. Phase 3 admin
revoke flows will extend this with ``set_status`` etc.

Issue #67: ``create_for_message`` upgraded from ``session.add`` + flush to
``ON CONFLICT DO NOTHING`` + SELECT fallback so that duplicate message delivery
(polling restart, retry) is a true no-op — no second audit row is created. The
conflict target is the partial unique index
``ix_offrecord_marks_chat_message_id_mark_type`` added by migration 013.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import OffrecordMark


class OffrecordMarkRepo:
    @staticmethod
    async def create_for_message(
        session: AsyncSession,
        chat_message_id: int,
        mark_type: str,
        detected_by: str,
        set_by_user_id: int | None = None,
        thread_id: int | None = None,
    ) -> OffrecordMark:
        """Insert a mark with ``scope_type='message'`` for a single chat_messages row.

        Idempotent on duplicate ``(chat_message_id, mark_type)`` pairs: uses
        ``ON CONFLICT DO NOTHING`` targeting the partial unique index
        ``ix_offrecord_marks_chat_message_id_mark_type`` (migration 013, Issue #67).
        When a conflict is detected (no row returned by RETURNING), fetches the
        existing row via a follow-up SELECT.

        Flushes; does not commit. Caller controls the transaction lifecycle (typically
        the chat_messages handler's session, which DbSessionMiddleware commits on
        handler success).

        ``mark_type`` must be ``'nomem'`` or ``'offrecord'`` — the DB CHECK enforces
        this; the repo does not pre-validate so the caller surfaces the postgres error
        directly.
        """
        values: dict = {
            "mark_type": mark_type,
            "scope_type": "message",
            "scope_id": str(chat_message_id),
            "chat_message_id": chat_message_id,
            "detected_by": detected_by,
            "status": "active",
        }
        if thread_id is not None:
            values["thread_id"] = thread_id
        if set_by_user_id is not None:
            values["set_by_user_id"] = set_by_user_id

        stmt = (
            pg_insert(OffrecordMark)
            .values(**values)
            .on_conflict_do_nothing(
                index_elements=["chat_message_id", "mark_type"],
            )
            .returning(OffrecordMark)
        )
        result = await session.execute(stmt)
        inserted = result.scalar_one_or_none()

        if inserted is not None:
            await session.flush()
            return inserted

        # Conflict path: the row already exists — no new audit row needed.
        existing = await session.execute(
            select(OffrecordMark).where(
                OffrecordMark.chat_message_id == chat_message_id,
                OffrecordMark.mark_type == mark_type,
            )
        )
        return existing.scalar_one()
