from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from tests.conftest import import_module

pytestmark = pytest.mark.usefixtures("app_env")


class _ExecuteResult:
    def __init__(self, value: int | None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> int | None:
        return self._value


class _Scalars:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self._rows = rows

    def all(self) -> list[SimpleNamespace]:
        return self._rows


class _RowsResult:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self._rows = rows

    def scalars(self) -> _Scalars:
        return _Scalars(self._rows)


class _SessionContext:
    def __init__(self, session: SimpleNamespace) -> None:
        self.session = session

    async def __aenter__(self) -> SimpleNamespace:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


def _callback() -> SimpleNamespace:
    bot = SimpleNamespace(
        delete_message=AsyncMock(),
        send_message=AsyncMock(),
        create_chat_invite_link=AsyncMock(),
    )
    return SimpleNamespace(
        from_user=SimpleNamespace(id=2001),
        message=SimpleNamespace(message_id=3001),
        bot=bot,
        answer=AsyncMock(),
    )


def test_vouch_inserts_outbox_row_no_invite_sent(monkeypatch) -> None:
    handler = import_module("bot.handlers.vouch")
    session = SimpleNamespace(
        execute=AsyncMock(return_value=_ExecuteResult(101)),
        flush=AsyncMock(),
    )
    callback = _callback()
    callback_data = SimpleNamespace(application_id=101)
    app = SimpleNamespace(id=101, user_id=3002)
    voucher = SimpleNamespace(id=2001, is_member=True, username="bob", first_name="Bob")

    monkeypatch.setattr(handler.ApplicationRepo, "get", AsyncMock(return_value=app))
    monkeypatch.setattr(handler.UserRepo, "get", AsyncMock(return_value=voucher))
    monkeypatch.setattr(handler.VouchRepo, "create", AsyncMock())
    monkeypatch.setattr(handler.InviteOutboxRepo, "create_pending", AsyncMock())

    asyncio.run(handler.handle_vouch(callback, callback_data, session))

    handler.InviteOutboxRepo.create_pending.assert_awaited_once_with(
        session,
        application_id=101,
        user_id=3002,
        chat_id=handler.settings.COMMUNITY_CHAT_ID,
    )
    callback.bot.create_chat_invite_link.assert_not_called()
    callback.answer.assert_awaited_once_with("Готово! Спасибо за ручательство.")


def test_ready_inserts_outbox_row_no_invite_sent(monkeypatch) -> None:
    handler = import_module("bot.handlers.vouch")
    session = SimpleNamespace()
    callback = SimpleNamespace(
        from_user=SimpleNamespace(id=3002),
        message=SimpleNamespace(edit_text=AsyncMock()),
        bot=SimpleNamespace(create_chat_invite_link=AsyncMock()),
        answer=AsyncMock(),
    )
    callback_data = SimpleNamespace(application_id=101)
    app = SimpleNamespace(id=101, user_id=3002, status="privacy_block")

    monkeypatch.setattr(handler.ApplicationRepo, "get", AsyncMock(return_value=app))
    monkeypatch.setattr(handler.ApplicationRepo, "update_status", AsyncMock())
    monkeypatch.setattr(handler.InviteOutboxRepo, "create_pending", AsyncMock())

    asyncio.run(handler.handle_ready(callback, callback_data, session))

    handler.ApplicationRepo.update_status.assert_awaited_once_with(
        session, 101, "vouched", invite_user_id=3002
    )
    handler.InviteOutboxRepo.create_pending.assert_awaited_once_with(
        session,
        application_id=101,
        user_id=3002,
        chat_id=handler.settings.COMMUNITY_CHAT_ID,
    )
    callback.bot.create_chat_invite_link.assert_not_called()
    callback.message.edit_text.assert_awaited_once_with(
        "Запрос принят. Инвайт скоро придёт в личные сообщения."
    )
    callback.answer.assert_awaited_once_with()


def test_outbox_worker_sends_pending(monkeypatch) -> None:
    worker = import_module("bot.services.invite_worker")
    row = SimpleNamespace(
        id=1,
        application_id=101,
        user_id=3002,
        chat_id=-100123,
        status="pending",
        invite_link=None,
        attempt_count=0,
        last_error=None,
        sent_at=None,
    )
    session = SimpleNamespace(commit=AsyncMock())
    bot = SimpleNamespace(send_message=AsyncMock())

    monkeypatch.setattr(worker, "async_session", lambda: _SessionContext(session))
    monkeypatch.setattr(worker.InviteOutboxRepo, "get_pending", AsyncMock(return_value=[row]))
    monkeypatch.setattr(worker.invite_service, "create_invite", AsyncMock(return_value="https://t.me/+ok"))

    asyncio.run(worker.process_invite_outbox(bot))

    worker.invite_service.create_invite.assert_awaited_once_with(
        bot, -100123, 101, 3002
    )
    bot.send_message.assert_awaited_once_with(
        chat_id=3002,
        text=worker.INVITE_LINK_MSG.format(link="https://t.me/+ok"),
    )
    assert row.status == "sent"
    assert row.invite_link == "https://t.me/+ok"
    assert row.sent_at is not None
    session.commit.assert_awaited_once()


def test_outbox_worker_retries_on_failure(monkeypatch) -> None:
    worker = import_module("bot.services.invite_worker")
    row = SimpleNamespace(
        id=1,
        application_id=101,
        user_id=3002,
        chat_id=-100123,
        status="pending",
        invite_link=None,
        attempt_count=0,
        last_error=None,
        sent_at=None,
    )
    session = SimpleNamespace(commit=AsyncMock())
    bot = SimpleNamespace(send_message=AsyncMock())

    monkeypatch.setattr(worker, "async_session", lambda: _SessionContext(session))
    monkeypatch.setattr(worker.InviteOutboxRepo, "get_pending", AsyncMock(return_value=[row]))
    monkeypatch.setattr(
        worker.invite_service,
        "create_invite",
        AsyncMock(side_effect=RuntimeError("telegram unavailable")),
    )

    asyncio.run(worker.process_invite_outbox(bot))

    assert row.status == "pending"
    assert row.attempt_count == 1
    assert row.last_error == "telegram unavailable"
    assert row.sent_at is None
    bot.send_message.assert_not_called()
    session.commit.assert_awaited_once()


def test_outbox_worker_marks_failed_after_5_attempts(monkeypatch) -> None:
    worker = import_module("bot.services.invite_worker")
    row = SimpleNamespace(
        id=1,
        application_id=101,
        user_id=3002,
        chat_id=-100123,
        status="pending",
        invite_link=None,
        attempt_count=4,
        last_error=None,
        sent_at=None,
    )
    session = SimpleNamespace(commit=AsyncMock())
    bot = SimpleNamespace(send_message=AsyncMock())

    monkeypatch.setattr(worker, "async_session", lambda: _SessionContext(session))
    monkeypatch.setattr(worker.InviteOutboxRepo, "get_pending", AsyncMock(return_value=[row]))
    monkeypatch.setattr(
        worker.invite_service,
        "create_invite",
        AsyncMock(side_effect=RuntimeError("privacy blocked")),
    )
    update_status_mock = AsyncMock()
    monkeypatch.setattr(worker.ApplicationRepo, "update_status", update_status_mock)

    asyncio.run(worker.process_invite_outbox(bot))

    assert row.status == "failed"
    assert row.attempt_count == 5
    assert row.last_error == "privacy blocked"
    update_status_mock.assert_awaited_once_with(session, 101, "privacy_block")
    bot.send_message.assert_awaited_once()
    session.commit.assert_awaited_once()


def test_invite_outbox_model_registered() -> None:
    models = import_module("bot.db.models")

    assert hasattr(models, "InviteOutbox")
    assert "invite_outbox" in models.Base.metadata.tables
    table = models.Base.metadata.tables["invite_outbox"]
    cols = {c.name for c in table.columns}
    assert {
        "id",
        "application_id",
        "user_id",
        "chat_id",
        "status",
        "invite_link",
        "attempt_count",
        "last_error",
        "created_at",
        "sent_at",
    } == cols
    assert "ix_invite_outbox_status" in {ix.name for ix in table.indexes}
