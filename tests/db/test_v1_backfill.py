"""T1-07 acceptance tests — v1 backfill via ``bot/services/backfill.py``.

The alembic migration 008 delegates to ``backfill_v1_message_versions`` so testing
the function directly proves the migration's behavior end-to-end (subject to the
async engine glue in the migration itself, which is hard to unit-test without a
fresh alembic environment).
"""

from __future__ import annotations

import itertools
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.usefixtures("app_env")

_user_counter = itertools.count(start=8_900_000_000)
_msg_counter = itertools.count(start=970_000)


def _next_user() -> int:
    return next(_user_counter)


def _next_msg_id() -> int:
    return next(_msg_counter)


def _random_chat_id() -> int:
    return -1_000_000_000_000 - (next(_msg_counter) % 1_000_000)


async def _make_legacy_chat_message(
    db_session, *, text: str | None = "legacy text", caption: str | None = None
) -> int:
    """Insert a chat_messages row simulating the gatekeeper-era shape (no
    current_version_id, no message_kind)."""
    from bot.db.models import ChatMessage
    from bot.db.repos.user import UserRepo

    user_id = _next_user()
    chat_id = _random_chat_id()
    when = datetime.now(timezone.utc)

    await UserRepo.upsert(
        db_session, telegram_id=user_id, username="u", first_name="U", last_name=None,
    )

    msg = ChatMessage(
        message_id=_next_msg_id(),
        chat_id=chat_id,
        user_id=user_id,
        text=text,
        caption=caption,
        date=when,
    )
    db_session.add(msg)
    await db_session.flush()
    return msg.id


# ─── happy path ────────────────────────────────────────────────────────────────────────────

async def test_backfill_creates_v1_for_each_legacy_row(db_session) -> None:
    from bot.db.models import ChatMessage, MessageVersion
    from bot.services.backfill import backfill_v1_message_versions

    msg_ids = [
        await _make_legacy_chat_message(db_session, text=f"row {i}")
        for i in range(5)
    ]

    count = await backfill_v1_message_versions(db_session, batch_size=10)
    assert count == 5

    for msg_id in msg_ids:
        msg = (
            await db_session.execute(
                select(ChatMessage).where(ChatMessage.id == msg_id)
            )
        ).scalar_one()
        await db_session.refresh(msg)
        assert msg.current_version_id is not None

        v = (
            await db_session.execute(
                select(MessageVersion).where(
                    MessageVersion.chat_message_id == msg_id
                )
            )
        ).scalar_one()
        assert v.version_seq == 1
        assert v.content_hash is not None
        assert len(v.content_hash) == 64  # sha256 hex
        # captured_at must be pinned to msg.date (HANDOFF.md §6 #5 + issue #31).
        assert v.captured_at == msg.date


# ─── idempotency ───────────────────────────────────────────────────────────────────────────

async def test_backfill_is_idempotent_on_rerun(db_session) -> None:
    from bot.services.backfill import backfill_v1_message_versions

    for i in range(3):
        await _make_legacy_chat_message(db_session, text=f"x{i}")

    first = await backfill_v1_message_versions(db_session, batch_size=10)
    second = await backfill_v1_message_versions(db_session, batch_size=10)

    assert first == 3
    assert second == 0  # nothing left to backfill


# ─── chunked / batched processing ─────────────────────────────────────────────────────────

async def test_backfill_chunks_correctly_when_more_rows_than_batch_size(db_session) -> None:
    from bot.services.backfill import backfill_v1_message_versions

    for i in range(7):
        await _make_legacy_chat_message(db_session, text=f"chunk{i}")

    count = await backfill_v1_message_versions(db_session, batch_size=2)
    assert count == 7


# ─── NULL text handled ─────────────────────────────────────────────────────────────────────

async def test_backfill_handles_null_text_rows(db_session) -> None:
    """Legacy rows where text is NULL (e.g. media messages) must still get a v1
    row with a stable hash."""
    from bot.db.models import MessageVersion
    from bot.services.backfill import backfill_v1_message_versions

    msg_id = await _make_legacy_chat_message(db_session, text=None, caption=None)

    count = await backfill_v1_message_versions(db_session)
    assert count == 1

    v = (
        await db_session.execute(
            select(MessageVersion).where(MessageVersion.chat_message_id == msg_id)
        )
    ).scalar_one()
    assert v.content_hash is not None
    assert len(v.content_hash) == 64


# ─── pre-existing v1 rows are not duplicated ───────────────────────────────────────────────

async def test_backfill_skips_messages_with_existing_current_version_id(db_session) -> None:
    """If a message already has current_version_id set (e.g. from live ingestion),
    the backfill must not touch it."""
    from bot.db.models import ChatMessage
    from bot.db.repos.message_version import MessageVersionRepo
    from bot.services.backfill import backfill_v1_message_versions

    pre_msg_id = await _make_legacy_chat_message(db_session, text="already wired")
    v = await MessageVersionRepo.insert_version(
        db_session,
        chat_message_id=pre_msg_id,
        content_hash="manual-hash",
        text="already wired",
    )
    msg = (
        await db_session.execute(
            select(ChatMessage).where(ChatMessage.id == pre_msg_id)
        )
    ).scalar_one()
    msg.current_version_id = v.id
    await db_session.flush()

    other_id = await _make_legacy_chat_message(db_session, text="needs backfill")

    count = await backfill_v1_message_versions(db_session)
    assert count == 1  # only the not-yet-wired message

    other_msg = (
        await db_session.execute(
            select(ChatMessage).where(ChatMessage.id == other_id)
        )
    ).scalar_one()
    await db_session.refresh(other_msg)
    assert other_msg.current_version_id is not None


# ─── content_hash deterministic ────────────────────────────────────────────────────────────

def test_compute_content_hash_deterministic(app_env) -> None:
    from bot.services.content_hash import compute_content_hash

    a = compute_content_hash(text="hello", caption=None, message_kind=None)
    b = compute_content_hash(text="hello", caption=None, message_kind=None)
    c = compute_content_hash(text="hello", caption=None, message_kind="text")
    d = compute_content_hash(text="HELLO", caption=None, message_kind=None)

    assert a == b  # same inputs → same hash
    assert a == c  # message_kind=None defaults to 'text', so same as explicit 'text'
    assert a != d  # case-sensitive


def test_compute_content_hash_handles_none(app_env) -> None:
    from bot.services.content_hash import compute_content_hash

    h = compute_content_hash(text=None, caption=None, message_kind=None)
    assert len(h) == 64  # sha256 hex


def test_compute_content_hash_includes_caption(app_env) -> None:
    from bot.services.content_hash import compute_content_hash

    a = compute_content_hash(text="hi", caption=None, message_kind=None)
    b = compute_content_hash(text="hi", caption="cap", message_kind=None)
    assert a != b
