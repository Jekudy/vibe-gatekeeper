from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.eval_runner import run_eval_recall

pytestmark = pytest.mark.usefixtures("app_env")


@pytest_asyncio.fixture()
async def empty_eval_session(db_session: AsyncSession) -> AsyncIterator[AsyncSession]:
    await db_session.execute(
        text(
            """
            TRUNCATE TABLE
                qa_traces,
                message_versions,
                chat_messages,
                forget_events
            RESTART IDENTITY CASCADE
            """
        )
    )
    yield db_session


async def test_run_eval_recall_empty_fixture_abstains(
    empty_eval_session: AsyncSession,
) -> None:
    bundle, trace = await run_eval_recall(
        empty_eval_session,
        query="nonexistent recall query",
        chat_id=-1001234567890,
    )

    assert bundle.abstained is True
    assert bundle.items == ()
    assert trace is None
