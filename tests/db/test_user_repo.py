"""T0-02 acceptance tests — UserRepo.upsert against real postgres.

These tests exercise the real ON CONFLICT DO UPDATE path and confirm:
- new row is inserted with the supplied fields
- repeat upsert with same telegram id updates fields without raising or duplicating
- the returned object is the persisted row (single row in the table)
- conflict on the primary key is resolved transparently

Tests are SKIPPED if no postgres is reachable (see conftest.postgres_engine). CI runs against
a postgres service container so this coverage runs on every PR.
"""

from __future__ import annotations

import pytest
from sqlalchemy import delete, select

# `app_env` from conftest sets DATABASE_URL via env var (CI sets the postgres service URL,
# local dev gets the docker-compose dev postgres URL). The `postgres_engine` fixture in
# conftest is the single resolver; no per-test override is needed.
pytestmark = pytest.mark.usefixtures("app_env")


async def _delete_user(session, telegram_id: int) -> None:
    from bot.db.models import User

    await session.execute(delete(User).where(User.id == telegram_id))
    await session.flush()


async def _count_users_with_id(session, telegram_id: int) -> int:
    from bot.db.models import User

    result = await session.execute(select(User).where(User.id == telegram_id))
    return len(result.scalars().all())


async def test_upsert_new_user_inserts_row(db_session) -> None:
    from bot.db.repos.user import UserRepo

    telegram_id = 1000_001
    await _delete_user(db_session, telegram_id)
    await db_session.commit()

    user = await UserRepo.upsert(
        db_session,
        telegram_id=telegram_id,
        username="newcomer",
        first_name="New",
        last_name="Comer",
    )
    await db_session.commit()

    assert user.id == telegram_id
    assert user.username == "newcomer"
    assert user.first_name == "New"
    assert user.last_name == "Comer"
    assert await _count_users_with_id(db_session, telegram_id) == 1

    await _delete_user(db_session, telegram_id)
    await db_session.commit()


async def test_upsert_existing_user_updates_fields_no_duplicate(db_session) -> None:
    from bot.db.repos.user import UserRepo

    telegram_id = 1000_002
    await _delete_user(db_session, telegram_id)
    await db_session.commit()

    await UserRepo.upsert(
        db_session,
        telegram_id=telegram_id,
        username="old_name",
        first_name="Old",
        last_name=None,
    )
    await db_session.commit()

    updated = await UserRepo.upsert(
        db_session,
        telegram_id=telegram_id,
        username="new_name",
        first_name="New",
        last_name="Surname",
    )
    await db_session.commit()

    assert updated.id == telegram_id
    assert updated.username == "new_name"
    assert updated.first_name == "New"
    assert updated.last_name == "Surname"
    assert await _count_users_with_id(db_session, telegram_id) == 1

    await _delete_user(db_session, telegram_id)
    await db_session.commit()


async def test_upsert_returns_row_after_insert(db_session) -> None:
    """Smoke test: the return value of upsert is the persisted row, not a transient copy."""
    from bot.db.models import User
    from bot.db.repos.user import UserRepo

    telegram_id = 1000_003
    await _delete_user(db_session, telegram_id)
    await db_session.commit()

    returned = await UserRepo.upsert(
        db_session,
        telegram_id=telegram_id,
        username="probe",
        first_name="Probe",
        last_name=None,
    )
    await db_session.commit()

    fetched = (await db_session.execute(select(User).where(User.id == telegram_id))).scalar_one()
    assert returned.id == fetched.id
    assert returned.username == fetched.username

    await _delete_user(db_session, telegram_id)
    await db_session.commit()


async def test_upsert_returns_row_after_update(db_session) -> None:
    """The return value after a conflict is the row reflecting the new values."""
    from bot.db.repos.user import UserRepo

    telegram_id = 1000_004
    await _delete_user(db_session, telegram_id)
    await db_session.commit()

    await UserRepo.upsert(
        db_session,
        telegram_id=telegram_id,
        username="first_iter",
        first_name="First",
        last_name=None,
    )
    await db_session.commit()

    updated = await UserRepo.upsert(
        db_session,
        telegram_id=telegram_id,
        username="second_iter",
        first_name="Second",
        last_name="Iteration",
    )
    await db_session.commit()

    assert updated.username == "second_iter"
    assert updated.first_name == "Second"
    assert updated.last_name == "Iteration"

    await _delete_user(db_session, telegram_id)
    await db_session.commit()


def test_engine_rejects_sqlite_url(monkeypatch) -> None:
    """Engine module must refuse a sqlite URL with a clear error pointing at T0-02."""
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///vibe_gatekeeper.db")
    # Force re-import so the module sees the new env var.
    import sys

    for name in list(sys.modules):
        if name == "bot.db.engine" or name == "bot.config":
            sys.modules.pop(name, None)

    with pytest.raises(RuntimeError, match="sqlite"):
        import bot.db.engine  # noqa: F401


def test_engine_rejects_empty_url(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    import sys

    for name in list(sys.modules):
        if name == "bot.db.engine" or name == "bot.config":
            sys.modules.pop(name, None)

    with pytest.raises(RuntimeError, match="DATABASE_URL is empty"):
        import bot.db.engine  # noqa: F401
