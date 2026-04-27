"""backfill_message_versions_v1

T1-07: walk legacy ``chat_messages`` rows (``current_version_id IS NULL``) and create
a ``message_versions`` v1 row for each. Sets ``chat_messages.current_version_id`` so
the operation is idempotent — re-running this migration after success is a no-op
because the WHERE clause excludes already-backfilled rows.

The migration delegates to ``bot/services/backfill.py`` so the same code path is
exercised by tests. Chunked (1000 rows per batch by default) to keep prod transaction
sizes bounded.

Revision ID: 008
Revises: 007
Create Date: 2026-04-27
"""

from __future__ import annotations

import asyncio
from typing import Sequence, Union

from alembic import op
from sqlalchemy.ext.asyncio import AsyncSession

revision: str = "008"
down_revision: Union[str, Sequence[str], None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


async def _run_async_backfill() -> int:
    """Run the async backfill in alembic's sync context.

    alembic uses a SYNC connection (env.py wraps it). We open an independent async
    engine bound to the same DATABASE_URL so the backfill code shares the live ORM
    layer. The migration commits at the end via this engine; alembic's outer
    transaction is unaffected.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from bot.config import settings
    from bot.services.backfill import backfill_v1_message_versions

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with Session() as session:
            # commit_per_batch=True so a 50k-row backfill does not hold one giant
            # transaction. Tests use the default (False) with outer-tx rollback for
            # isolation.
            count = await backfill_v1_message_versions(session, commit_per_batch=True)
            # Final commit covers the (possibly partial) trailing batch that did not
            # reach the per-batch commit branch.
            await session.commit()
            return count
    finally:
        await engine.dispose()


def upgrade() -> None:
    # Use op.get_bind() only to confirm we're on postgres; backfill itself runs via
    # an independent async engine (see _run_async_backfill).
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect != "postgresql":
        raise RuntimeError(
            f"T1-07 backfill requires postgres (got {dialect!r}). See T0-02."
        )

    count = asyncio.run(_run_async_backfill())
    print(f"[T1-07] backfilled v1 message_versions for {count} chat_messages rows")


def downgrade() -> None:
    """Wipe v1 versions created by the backfill and reset current_version_id.

    Targets only ``version_seq=1`` rows whose ``raw_update_id IS NULL`` (heuristic for
    backfilled rows — live ingestion writes raw_update_id once T1-04+T1-14 land). On
    a fresh DB this is a clean reverse; on a DB where post-backfill v2/v3 versions
    exist for the same messages, those survive. Operators should not normally
    downgrade this migration — it's here for completeness.
    """
    bind = op.get_bind()
    bind.execute(
        op.text(
            "UPDATE chat_messages SET current_version_id = NULL "
            "WHERE current_version_id IN ("
            "  SELECT id FROM message_versions "
            "  WHERE version_seq = 1 AND raw_update_id IS NULL"
            ")"
        )
    )
    bind.execute(
        op.text(
            "DELETE FROM message_versions "
            "WHERE version_seq = 1 AND raw_update_id IS NULL"
        )
    )
