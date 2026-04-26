from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, call

from tests.conftest import import_module


def _message(requester_id: int, text: str = "stored community message") -> SimpleNamespace:
    return SimpleNamespace(
        from_user=SimpleNamespace(id=requester_id),
        text=text,
        answer=AsyncMock(),
    )


def _user(
    user_id: int,
    *,
    is_member: bool,
    is_admin: bool = False,
    first_name: str = "Alice",
    username: str | None = "alice",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=user_id,
        is_member=is_member,
        is_admin=is_admin,
        first_name=first_name,
        username=username,
    )


def _chat_message(author_id: int = 222) -> SimpleNamespace:
    return SimpleNamespace(user_id=author_id)


def _intro(text: str = "private intro text") -> SimpleNamespace:
    return SimpleNamespace(intro_text=text)


def test_forward_lookup_member_can_lookup(app_env, monkeypatch) -> None:
    handler = import_module("bot.handlers.forward_lookup")
    session = AsyncMock()
    message = _message(requester_id=111)

    user_get = AsyncMock(side_effect=[_user(111, is_member=True), _user(222, is_member=True)])
    message_lookup = AsyncMock(return_value=_chat_message())
    intro_get = AsyncMock(return_value=_intro())

    monkeypatch.setattr(handler.UserRepo, "get", user_get)
    monkeypatch.setattr(handler.MessageRepo, "find_by_exact_text", message_lookup)
    monkeypatch.setattr(handler.IntroRepo, "get", intro_get)

    asyncio.run(handler.handle_forwarded_message(message, session))

    user_get.assert_has_awaits([call(session, 111), call(session, 222)])
    message_lookup.assert_awaited_once_with(session, "stored community message")
    intro_get.assert_awaited_once_with(session, 222)
    message.answer.assert_awaited_once()
    answer_text = message.answer.await_args.args[0]
    assert "Alice" in answer_text
    assert "alice" in answer_text
    assert "private intro text" in answer_text


def test_forward_lookup_non_member_denied(app_env, monkeypatch) -> None:
    handler = import_module("bot.handlers.forward_lookup")
    session = AsyncMock()
    message = _message(requester_id=111)

    user_get = AsyncMock(return_value=_user(111, is_member=False))
    message_lookup = AsyncMock(return_value=_chat_message())
    intro_get = AsyncMock(return_value=_intro())

    monkeypatch.setattr(handler.UserRepo, "get", user_get)
    monkeypatch.setattr(handler.MessageRepo, "find_by_exact_text", message_lookup)
    monkeypatch.setattr(handler.IntroRepo, "get", intro_get)

    asyncio.run(handler.handle_forwarded_message(message, session))

    user_get.assert_awaited_once_with(session, 111)
    message_lookup.assert_not_called()
    intro_get.assert_not_called()
    message.answer.assert_not_called()
    assert all("Alice" not in args.args for args in message.answer.await_args_list)
    assert all("private intro text" not in args.args for args in message.answer.await_args_list)


def test_forward_lookup_admin_can_lookup(app_env, monkeypatch) -> None:
    handler = import_module("bot.handlers.forward_lookup")
    session = AsyncMock()
    message = _message(requester_id=333)

    user_get = AsyncMock(
        side_effect=[
            _user(333, is_member=False, is_admin=True),
            _user(222, is_member=True),
        ]
    )
    message_lookup = AsyncMock(return_value=_chat_message())
    intro_get = AsyncMock(return_value=_intro())

    monkeypatch.setattr(handler.UserRepo, "get", user_get)
    monkeypatch.setattr(handler.MessageRepo, "find_by_exact_text", message_lookup)
    monkeypatch.setattr(handler.IntroRepo, "get", intro_get)

    asyncio.run(handler.handle_forwarded_message(message, session))

    user_get.assert_has_awaits([call(session, 333), call(session, 222)])
    message_lookup.assert_awaited_once_with(session, "stored community message")
    intro_get.assert_awaited_once_with(session, 222)
    message.answer.assert_awaited_once()
    answer_text = message.answer.await_args.args[0]
    assert "Alice" in answer_text
    assert "alice" in answer_text
    assert "private intro text" in answer_text
