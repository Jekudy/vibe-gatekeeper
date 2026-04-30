"""Governance-filtered full-text search for Phase 4 memory retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class SearchHit:
    message_version_id: int
    chat_id: int
    message_id: int
    snippet: str
    ts_rank: float
    captured_at: datetime


async def search_messages(
    session: AsyncSession,
    query: str,
    *,
    chat_id: int,
    limit: int = 10,
) -> list[SearchHit]:
    """Search visible message versions in one chat.

    The governance filter is intentionally repeated here even though migration 020
    also creates a partial GIN index for redacted versions. Search consumers must
    not depend on index shape for privacy.
    """
    normalized_query = query.strip()
    if not normalized_query:
        return []
    if limit < 1:
        raise ValueError("limit must be >= 1")

    stmt = text(
        """
        WITH q AS (
            SELECT plainto_tsquery('russian', :query) AS tsq
        )
        SELECT
            mv.id AS message_version_id,
            c.chat_id AS chat_id,
            c.message_id AS message_id,
            COALESCE(
                ts_headline(
                    'russian',
                    concat_ws(' ', mv.text, mv.caption),
                    q.tsq,
                    'MaxWords=20, MinWords=5'
                ),
                ''
            ) AS snippet,
            ts_rank(mv.tsv, q.tsq) AS rank,
            mv.captured_at AS captured_at
        FROM message_versions AS mv
        JOIN chat_messages AS c ON mv.chat_message_id = c.id
        CROSS JOIN q
        LEFT JOIN forget_events AS fe
            ON fe.target_type = 'message'
            AND fe.target_id ~ '^[0-9]+$'
            AND fe.target_id::int = c.id
            AND fe.status IN ('pending', 'processing', 'completed')
        WHERE c.chat_id = :chat_id
            AND c.memory_policy = 'normal'
            AND c.is_redacted = FALSE
            AND mv.is_redacted = FALSE
            AND fe.id IS NULL
            AND mv.tsv @@ q.tsq
        ORDER BY rank DESC, mv.captured_at DESC, mv.id DESC
        LIMIT :limit
        """
    )
    result = await session.execute(
        stmt,
        {
            "query": normalized_query,
            "chat_id": chat_id,
            "limit": limit,
        },
    )

    return [
        SearchHit(
            message_version_id=row["message_version_id"],
            chat_id=row["chat_id"],
            message_id=row["message_id"],
            snippet=row["snippet"],
            ts_rank=float(row["rank"]),
            captured_at=row["captured_at"],
        )
        for row in result.mappings().all()
    ]
