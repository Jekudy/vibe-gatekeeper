"""Repository for ``forget_events`` (T3-01).

Thin data-access layer for forget/tombstone events. Sprint 3 (#96) adds the cascade
worker that drives status transitions; this repo exposes only the primitives needed
by that worker and by the forget commands (Sprints 2 / 4 — #95 / #105).

Status lifecycle: pending → processing → completed | failed.
Allowed transitions:
  - pending → processing
  - processing → completed
  - processing → failed

Any other transition raises ``ValueError`` immediately (before any DB call).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import ForgetEvent

# Valid transitions: key = current status, value = set of allowed next statuses.
_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"processing"}),
    "processing": frozenset({"completed", "failed"}),
    "completed": frozenset(),
    "failed": frozenset(),
}


class ForgetEventRepo:
    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        target_type: str,
        target_id: str | None,
        actor_user_id: int | None,
        authorized_by: str,
        tombstone_key: str,
        reason: str | None = None,
        policy: str = "forgotten",
    ) -> ForgetEvent:
        """Insert a new ForgetEvent; return existing row if tombstone_key already taken.

        Idempotent on ``tombstone_key``: re-issuing a forget for the same target
        returns the existing row without raising or creating a duplicate.

        Flushes; does not commit. Caller controls the transaction lifecycle.
        """
        existing = await ForgetEventRepo.get_by_tombstone_key(session, tombstone_key)
        if existing is not None:
            return existing

        row = ForgetEvent(
            target_type=target_type,
            target_id=target_id,
            actor_user_id=actor_user_id,
            authorized_by=authorized_by,
            tombstone_key=tombstone_key,
            reason=reason,
            policy=policy,
            status="pending",
        )
        session.add(row)
        await session.flush()
        return row

    @staticmethod
    async def get_by_tombstone_key(
        session: AsyncSession,
        tombstone_key: str,
    ) -> ForgetEvent | None:
        """Return the row matching ``tombstone_key``, or ``None`` if not found."""
        result = await session.execute(
            select(ForgetEvent).where(ForgetEvent.tombstone_key == tombstone_key)
        )
        return result.scalars().first()

    @staticmethod
    async def list_pending(
        session: AsyncSession,
        limit: int = 100,
    ) -> list[ForgetEvent]:
        """Return up to ``limit`` pending rows ordered by ``created_at`` ASC.

        Used by the cascade worker (Sprint 3) to fetch the next batch to process.
        """
        result = await session.execute(
            select(ForgetEvent)
            .where(ForgetEvent.status == "pending")
            .order_by(ForgetEvent.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def mark_status(
        session: AsyncSession,
        forget_event_id: int,
        *,
        status: str,
        cascade_status: dict | None = None,
    ) -> ForgetEvent:
        """Update status (and optionally cascade_status) of an existing ForgetEvent.

        Enforces the lifecycle state machine:
          - pending → processing
          - processing → completed
          - processing → failed

        Raises ``ValueError`` immediately (before any DB call) if the transition is
        invalid. This includes unknown statuses and backward / skip transitions such
        as ``completed → processing``.

        Flushes; does not commit. Caller controls the transaction lifecycle.
        """
        if status not in _ALLOWED_TRANSITIONS:
            raise ValueError(
                f"Unknown forget_event status {status!r}. "
                f"Must be one of: {sorted(_ALLOWED_TRANSITIONS)}"
            )

        result = await session.execute(
            select(ForgetEvent).where(ForgetEvent.id == forget_event_id)
        )
        row = result.scalars().one()

        allowed_next = _ALLOWED_TRANSITIONS.get(row.status, frozenset())
        if status not in allowed_next:
            raise ValueError(
                f"Invalid status transition for ForgetEvent(id={forget_event_id}): "
                f"{row.status!r} → {status!r}. "
                f"Allowed from {row.status!r}: {sorted(allowed_next) or '[]'}"
            )

        row.status = status
        if cascade_status is not None:
            row.cascade_status = cascade_status
        row.updated_at = datetime.now(timezone.utc)
        await session.flush()
        return row
