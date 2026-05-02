"""Offline evaluation runner for the production recall service path."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import QaTrace
from bot.services.evidence import EvidenceBundle
from bot.services.qa import run_qa


async def run_eval_recall(
    session: AsyncSession,
    *,
    query: str,
    chat_id: int,
    redact_query_in_audit: bool = False,
) -> tuple[EvidenceBundle, QaTrace | None]:
    """Call the same recall service used by production and expose its bundle."""
    result = await run_qa(
        session,
        query=query,
        chat_id=chat_id,
        redact_query_in_audit=redact_query_in_audit,
    )
    return result.bundle, None
