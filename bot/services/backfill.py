"""Backfill helpers (T1-07 v1 message_versions).

The backfill walks ``chat_messages`` rows where ``current_version_id IS NULL`` (legacy
rows from before T1-06), computes a content hash, inserts a ``message_versions`` row
with ``version_seq=1``, and sets ``chat_messages.current_version_id``. The query's
WHERE clause makes the operation idempotent — re-running after success is a no-op
because every targeted row will have ``current_version_id`` set.

Chunked: 1000 rows per batch by default to keep prod transaction sizes bounded. Each
batch commits independently when the caller commits between calls; the tests use a
single test transaction with one batch and rollback for isolation.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import ChatMessage, MessageVersion
from bot.services.content_hash import compute_content_hash

DEFAULT_BATCH_SIZE = 1000


async def backfill_v1_message_versions(
    session: AsyncSession, batch_size: int = DEFAULT_BATCH_SIZE
) -> int:
    """Backfill v1 ``message_versions`` for legacy ``chat_messages`` rows.

    Walks rows where ``current_version_id IS NULL`` in batches of ``batch_size``. For
    each row: insert a ``message_versions`` row with ``version_seq=1`` and the computed
    ``content_hash``, then set ``chat_messages.current_version_id``. Flushes after every
    batch.

    Returns the total number of rows backfilled in this call.
    """
    total = 0
    while True:
        result = await session.execute(
            select(ChatMessage)
            .where(ChatMessage.current_version_id.is_(None))
            .order_by(ChatMessage.id)
            .limit(batch_size)
        )
        batch = result.scalars().all()
        if not batch:
            break

        for msg in batch:
            content_hash = compute_content_hash(
                text=msg.text,
                caption=msg.caption,
                message_kind=msg.message_kind,
                entities_json=None,
            )
            version = MessageVersion(
                chat_message_id=msg.id,
                version_seq=1,
                text=msg.text,
                caption=msg.caption,
                normalized_text=msg.text,
                entities_json=None,
                edit_date=None,
                captured_at=datetime.now(tz=timezone.utc),
                content_hash=content_hash,
                raw_update_id=msg.raw_update_id,
                is_redacted=msg.is_redacted,
            )
            session.add(version)
            await session.flush()  # need version.id for the chat_messages update below

            await session.execute(
                update(ChatMessage)
                .where(ChatMessage.id == msg.id)
                .values(current_version_id=version.id)
            )
            total += 1

        await session.flush()

        # If we got fewer than batch_size, no more rows to process.
        if len(batch) < batch_size:
            break

    return total
