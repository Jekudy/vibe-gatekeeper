from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import InviteOutbox


class InviteOutboxRepo:
    @staticmethod
    async def create_pending(
        session: AsyncSession,
        application_id: int,
        user_id: int,
        chat_id: int,
    ) -> InviteOutbox:
        row = InviteOutbox(
            application_id=application_id,
            user_id=user_id,
            chat_id=chat_id,
            status="pending",
        )
        session.add(row)
        await session.flush()
        return row

    @staticmethod
    async def get_pending(session: AsyncSession, limit: int = 10) -> list[InviteOutbox]:
        result = await session.execute(
            select(InviteOutbox).where(InviteOutbox.status == "pending").limit(limit)
        )
        return list(result.scalars().all())
