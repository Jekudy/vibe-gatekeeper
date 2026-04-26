"""T0-03 acceptance tests — MessageRepo.save is idempotent on (chat_id, message_id).

Test isolation: each test runs inside the ``db_session`` fixture's outer transaction which
is rolled back at fixture teardown. Tests do NOT call ``session.commit()`` — they call
``MessageRepo.save()`` (which flushes internally on the first insert) and verify state with
``session.execute(select(...))``.

Tests use random telegram ids and random message ids (high range, randomized per test) so
any leaked rows from a prior failed run cannot collide and concurrent test runs cannot
interfere.

Tests are SKIPPED if no postgres is reachable (see ``conftest.postgres_engine``).
"""

from __future__ import annotations

import random
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.usefixtures("app_env")


def _random_user_id() -> int:
    return random.randint(900_000_000, 999_999_999)


def _random_chat_id() -> int:
    # Telegram supergroup ids are negative bigints starting with -100.
    return -1_000_000_000_000 - random.randint(0, 999_999)


def _random_message_id() -> int:
    return random.randint(100_000, 999_999)


async def _create_user(session, telegram_id: int) -> None:
    """Insert a minimal User row so chat_messages FK is satisfied."""
    from bot.db.repos.user import UserRepo

    await UserRepo.upsert(
        session,
        telegram_id=telegram_id,
        username=f"u{telegram_id}",
        first_name="Test",
        last_name=None,
    )


async def _count_messages(session, chat_id: int, message_id: int) -> int:
    from bot.db.models import ChatMessage

    result = await session.execute(
        select(ChatMessage).where(
            ChatMessage.chat_id == chat_id,
            ChatMessage.message_id == message_id,
        )
    )
    return len(result.scalars().all())


async def test_save_new_message_inserts_row(db_session) -> None:
    from bot.db.repos.message import MessageRepo

    user_id = _random_user_id()
    chat_id = _random_chat_id()
    message_id = _random_message_id()
    when = datetime.now(timezone.utc)

    await _create_user(db_session, user_id)

    saved = await MessageRepo.save(
        db_session,
        message_id=message_id,
        chat_id=chat_id,
        user_id=user_id,
        text="hello",
        date=when,
        raw_json={"k": "v"},
    )

    assert saved.id is not None
    assert saved.chat_id == chat_id
    assert saved.message_id == message_id
    assert saved.user_id == user_id
    assert saved.text == "hello"
    assert await _count_messages(db_session, chat_id, message_id) == 1


async def test_save_duplicate_returns_existing_no_error(db_session) -> None:
    """Repeat save with same (chat_id, message_id) must NOT raise and must return the
    existing row's id."""
    from bot.db.repos.message import MessageRepo

    user_id = _random_user_id()
    chat_id = _random_chat_id()
    message_id = _random_message_id()
    when = datetime.now(timezone.utc)

    await _create_user(db_session, user_id)

    first = await MessageRepo.save(
        db_session,
        message_id=message_id,
        chat_id=chat_id,
        user_id=user_id,
        text="hello",
        date=when,
        raw_json=None,
    )

    second = await MessageRepo.save(
        db_session,
        message_id=message_id,
        chat_id=chat_id,
        user_id=user_id,
        text="hello (would be duplicate)",
        date=when,
        raw_json=None,
    )

    assert second.id == first.id
    assert second.chat_id == first.chat_id
    assert second.message_id == first.message_id


async def test_save_duplicate_does_not_create_duplicate_row(db_session) -> None:
    from bot.db.repos.message import MessageRepo

    user_id = _random_user_id()
    chat_id = _random_chat_id()
    message_id = _random_message_id()
    when = datetime.now(timezone.utc)

    await _create_user(db_session, user_id)

    await MessageRepo.save(
        db_session,
        message_id=message_id,
        chat_id=chat_id,
        user_id=user_id,
        text="first",
        date=when,
        raw_json=None,
    )
    await MessageRepo.save(
        db_session,
        message_id=message_id,
        chat_id=chat_id,
        user_id=user_id,
        text="second",
        date=when,
        raw_json=None,
    )
    await MessageRepo.save(
        db_session,
        message_id=message_id,
        chat_id=chat_id,
        user_id=user_id,
        text="third",
        date=when,
        raw_json=None,
    )

    assert await _count_messages(db_session, chat_id, message_id) == 1


async def test_save_duplicate_preserves_first_inserted_text(db_session) -> None:
    """The architect's contract is "duplicate-safe save". Existing text is NOT overwritten
    on duplicate (Phase 1 message_versions will handle edits properly). The returned row's
    text equals the FIRST insert's text."""
    from bot.db.repos.message import MessageRepo

    user_id = _random_user_id()
    chat_id = _random_chat_id()
    message_id = _random_message_id()
    when = datetime.now(timezone.utc)

    await _create_user(db_session, user_id)

    await MessageRepo.save(
        db_session,
        message_id=message_id,
        chat_id=chat_id,
        user_id=user_id,
        text="original",
        date=when,
        raw_json=None,
    )

    second = await MessageRepo.save(
        db_session,
        message_id=message_id,
        chat_id=chat_id,
        user_id=user_id,
        text="changed text — must NOT overwrite",
        date=when,
        raw_json=None,
    )

    assert second.text == "original"


async def test_save_different_messages_in_same_chat_both_persist(db_session) -> None:
    from bot.db.repos.message import MessageRepo

    user_id = _random_user_id()
    chat_id = _random_chat_id()
    when = datetime.now(timezone.utc)

    await _create_user(db_session, user_id)

    msg_id_a = _random_message_id()
    msg_id_b = _random_message_id()
    while msg_id_b == msg_id_a:
        msg_id_b = _random_message_id()

    await MessageRepo.save(
        db_session,
        message_id=msg_id_a,
        chat_id=chat_id,
        user_id=user_id,
        text="A",
        date=when,
        raw_json=None,
    )
    await MessageRepo.save(
        db_session,
        message_id=msg_id_b,
        chat_id=chat_id,
        user_id=user_id,
        text="B",
        date=when,
        raw_json=None,
    )

    assert await _count_messages(db_session, chat_id, msg_id_a) == 1
    assert await _count_messages(db_session, chat_id, msg_id_b) == 1
