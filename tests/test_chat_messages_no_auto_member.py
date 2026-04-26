from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from tests.conftest import import_module


def test_save_chat_message_does_not_auto_mark_member(app_env, monkeypatch) -> None:
    handler = import_module("bot.handlers.chat_messages")
    session = AsyncMock()
    raw_json = {"message_id": 101, "text": "hello from chat"}
    message_date = datetime.now(timezone.utc)
    message = SimpleNamespace(
        message_id=101,
        chat=SimpleNamespace(id=-1001234567890),
        from_user=SimpleNamespace(
            id=222,
            username="not_member_yet",
            first_name="Alice",
            last_name="Example",
        ),
        text="hello from chat",
        date=message_date,
        model_dump=Mock(return_value=raw_json),
    )

    user_upsert = AsyncMock()
    user_set_member = AsyncMock()
    message_save = AsyncMock()

    monkeypatch.setattr(handler.UserRepo, "upsert", user_upsert)
    monkeypatch.setattr(handler.UserRepo, "set_member", user_set_member)
    monkeypatch.setattr(handler.MessageRepo, "save", message_save)

    asyncio.run(handler.save_chat_message(message, session))

    user_upsert.assert_awaited_once_with(
        session,
        telegram_id=222,
        username="not_member_yet",
        first_name="Alice",
        last_name="Example",
    )
    user_set_member.assert_not_called()
    message_save.assert_awaited_once_with(
        session,
        message_id=101,
        chat_id=-1001234567890,
        user_id=222,
        text="hello from chat",
        date=message_date,
        raw_json=raw_json,
    )
