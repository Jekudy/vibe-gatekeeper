from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.evidence import EvidenceBundle
from bot.services.search import search_messages


@dataclass(frozen=True)
class QaResult:
    bundle: EvidenceBundle
    query_redacted: bool


async def run_qa(
    session: AsyncSession,
    *,
    query: str,
    chat_id: int,
    redact_query_in_audit: bool,
    limit: int = 3,
) -> QaResult:
    hits = await search_messages(session, query, chat_id=chat_id, limit=limit)
    bundle = EvidenceBundle.from_hits(query, chat_id, hits)
    return QaResult(bundle=bundle, query_redacted=redact_query_in_audit)
