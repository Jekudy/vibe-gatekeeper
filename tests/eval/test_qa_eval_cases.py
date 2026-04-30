from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

pytestmark = pytest.mark.usefixtures("app_env")

EVAL_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "qa_eval_cases.json"


def _parse_dt(value: str | None) -> datetime:
    if value is None:
        return datetime.fromisoformat("2026-04-30T12:00:00+00:00")
    return datetime.fromisoformat(value)


async def _create_message(db_session, case_id: str, message: dict) -> None:
    from bot.db.models import ChatMessage, MessageVersion
    from bot.db.repos.user import UserRepo

    user_id = int(message["user_id"])
    await UserRepo.upsert(
        db_session,
        telegram_id=user_id,
        username=f"qa_eval_{user_id}",
        first_name=f"Eval {user_id}",
        last_name=None,
    )

    captured_at = _parse_dt(message.get("captured_at"))
    text = message.get("text", message.get("normalized_text"))
    caption = message.get("caption")
    content_hash = message.get("content_hash") or f"{case_id}-{message['message_id']}"
    is_redacted = bool(message.get("is_redacted", False))

    chat_message = ChatMessage(
        message_id=int(message["message_id"]),
        chat_id=int(message["chat_id"]),
        user_id=user_id,
        text=text,
        caption=caption,
        date=captured_at,
        memory_policy=message.get("memory_policy", "normal"),
        is_redacted=is_redacted,
        content_hash=content_hash,
    )
    db_session.add(chat_message)
    await db_session.flush()

    version = MessageVersion(
        chat_message_id=chat_message.id,
        version_seq=1,
        text=text,
        caption=caption,
        normalized_text=message.get("normalized_text"),
        content_hash=content_hash,
        is_redacted=is_redacted,
        captured_at=captured_at,
    )
    db_session.add(version)
    await db_session.flush()

    chat_message.current_version_id = version.id
    await db_session.flush()


async def _create_forget_event(db_session, event: dict) -> None:
    from bot.db.repos.forget_event import ForgetEventRepo

    row = await ForgetEventRepo.create(
        db_session,
        target_type=event["target_type"],
        target_id=event.get("target_id"),
        actor_user_id=None,
        authorized_by="system",
        tombstone_key=event["tombstone_key"],
    )
    status = event.get("status", "pending")
    if status == "pending":
        return

    await ForgetEventRepo.mark_status(db_session, row.id, status="processing")
    if status == "completed":
        await ForgetEventRepo.mark_status(db_session, row.id, status="completed")


async def _populate_case(db_session, case: dict) -> int:
    for message in case["fixture_messages"]:
        await _create_message(db_session, case["id"], message)
    for event in case.get("fixture_forget_events", []):
        await _create_forget_event(db_session, event)
    return int(case["fixture_messages"][0]["chat_id"])


CASES = json.loads(EVAL_FIXTURE.read_text())


@pytest.mark.parametrize("case", CASES, ids=lambda item: item["id"])
async def test_eval_case(case: dict, db_session) -> None:
    from bot.services.qa import run_qa

    chat_id = await _populate_case(db_session, case)
    result = await run_qa(
        db_session,
        query=case["query"],
        chat_id=chat_id,
        redact_query_in_audit=False,
    )

    expected_ids = case["expected_chat_message_ids"]
    if not case["expected_evidence_present"]:
        assert result.bundle.abstained is True, f"{case['id']}: expected abstention"
        assert result.bundle.items == ()
        return

    actual_ids = [item.message_id for item in result.bundle.items]
    assert actual_ids[: len(expected_ids)] == expected_ids, (
        f"{case['id']}: expected leading message_ids {expected_ids}, got {actual_ids}"
    )
