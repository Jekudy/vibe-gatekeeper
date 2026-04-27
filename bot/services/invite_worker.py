from __future__ import annotations

import logging
from datetime import datetime, timezone

from aiogram import Bot

from bot.db.engine import async_session
from bot.db.repos.invite_outbox import InviteOutboxRepo
from bot.services import invite as invite_service
from bot.texts import INVITE_LINK_MSG

logger = logging.getLogger(__name__)

MAX_INVITE_ATTEMPTS = 5
INVITE_OUTBOX_BATCH_SIZE = 10


async def process_invite_outbox(bot: Bot) -> None:
    async with async_session() as session:
        rows = await InviteOutboxRepo.get_pending(
            session, limit=INVITE_OUTBOX_BATCH_SIZE
        )
        for row in rows:
            try:
                link = await invite_service.create_invite(
                    bot, row.chat_id, row.application_id, row.user_id
                )
                await bot.send_message(
                    chat_id=row.user_id,
                    text=INVITE_LINK_MSG.format(link=link),
                )
                row.status = "sent"
                row.invite_link = link
                row.sent_at = datetime.now(timezone.utc)
                logger.info(
                    "Sent invite outbox row %s for app %s to user %s",
                    row.id,
                    row.application_id,
                    row.user_id,
                )
            except Exception as exc:
                row.attempt_count += 1
                row.last_error = str(exc)[:500]
                if row.attempt_count >= MAX_INVITE_ATTEMPTS:
                    row.status = "failed"
                logger.warning(
                    "Invite outbox row %s failed attempt %s/%s for app %s: %s",
                    row.id,
                    row.attempt_count,
                    MAX_INVITE_ATTEMPTS,
                    row.application_id,
                    exc,
                )
            await session.commit()
