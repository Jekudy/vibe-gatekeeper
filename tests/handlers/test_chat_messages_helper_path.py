"""End-to-end integration test: poll with #offrecord through the handler (Sprint #89 Commit 3).

Proves that after migrating chat_messages.py to use persist_message_with_policy, the
broadened detection (poll_question kwarg added in Commit 2) works end-to-end through the
real handler + real DB.

Strategy:
- DB-backed test (requires postgres via db_session fixture).
- Builds a SimpleNamespace message that carries a poll whose question contains #offrecord.
- Calls save_chat_message directly.
- Asserts:
  1. chat_messages row exists with memory_policy='offrecord' and is_redacted=True.
  2. offrecord_marks row exists for the saved row.

If postgres is unavailable, the test is auto-skipped (consistent with all other DB-backed
tests in this repo).
"""

from __future__ import annotations

import itertools
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.usefixtures("app_env")

_user_counter = itertools.count(start=9_400_000_000)
_msg_counter = itertools.count(start=940_000)

COMMUNITY_CHAT_ID = -1001234567890


def _make_poll_offrecord_message(*, message_id: int, user_id: int) -> SimpleNamespace:
    """Message with a poll whose question contains #offrecord (no text field)."""
    return SimpleNamespace(
        message_id=message_id,
        chat=SimpleNamespace(id=COMMUNITY_CHAT_ID, type="supergroup"),
        from_user=SimpleNamespace(
            id=user_id,
            username=f"u{user_id}",
            first_name="PollTest",
            last_name=None,
        ),
        text=None,
        caption=None,
        date=datetime.now(timezone.utc),
        model_dump=Mock(return_value={"message_id": message_id}),
        reply_to_message=None,
        message_thread_id=None,
        photo=None,
        video=None,
        voice=None,
        audio=None,
        document=None,
        sticker=None,
        animation=None,
        video_note=None,
        location=None,
        contact=None,
        # Poll with #offrecord in question
        poll=SimpleNamespace(
            question="What do you think? #offrecord",
            options=[SimpleNamespace(text="Yes"), SimpleNamespace(text="No")],
        ),
        dice=None,
        forward_origin=None,
        new_chat_members=None,
        left_chat_member=None,
        pinned_message=None,
        entities=None,
        caption_entities=None,
    )


async def test_handler_poll_offrecord_persisted_correctly(db_session) -> None:
    """Poll with #offrecord in question: handler saves row with offrecord policy.

    Verifies the helper-broadened detection works end-to-end through the handler.
    """
    from bot.db.models import ChatMessage, OffrecordMark
    from bot.handlers.chat_messages import save_chat_message

    user_id = next(_user_counter)
    msg_id = next(_msg_counter)

    message = _make_poll_offrecord_message(message_id=msg_id, user_id=user_id)

    await save_chat_message(message, db_session)

    # 1. chat_messages row has offrecord policy
    chat_msg = await db_session.scalar(
        select(ChatMessage).where(
            ChatMessage.chat_id == COMMUNITY_CHAT_ID,
            ChatMessage.message_id == msg_id,
        )
    )
    assert chat_msg is not None, "chat_messages row not found after handler call"
    assert chat_msg.memory_policy == "offrecord", (
        f"Expected memory_policy='offrecord', got {chat_msg.memory_policy!r}"
    )
    assert chat_msg.is_redacted is True, "Expected is_redacted=True for offrecord poll"
    assert chat_msg.text is None, "Expected text=None (redacted) for offrecord poll"

    # 2. offrecord_marks row exists
    mark_count = await db_session.scalar(
        select(__import__("sqlalchemy", fromlist=["func"]).func.count())
        .select_from(OffrecordMark)
        .where(OffrecordMark.chat_message_id == chat_msg.id)
    )
    assert mark_count == 1, (
        f"Expected 1 offrecord_marks row, got {mark_count}"
    )
