"""Repository for ``ingestion_runs`` (T1-02).

The repo intentionally exposes only the operations the ingestion service needs:
``create``, ``update_status``, and ``get_active_live`` (used by the live ingestion service
at startup to find or open a long-lived ``run_type='live'`` row). Heavier reporting
queries (per-period stats, list-all-failed) are out of scope for T1-02 and will be added
when the admin review UI lands later.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import IngestionRun

# Allowed run_type / status values mirror the CheckConstraint in the migration.
_ALLOWED_RUN_TYPES = {"live", "import", "dry_run", "cancelled"}
_TERMINAL_STATUSES = {"completed", "failed", "dry_run", "cancelled"}
_ALLOWED_STATUSES = {"running"} | _TERMINAL_STATUSES


class IngestionRunRepo:
    @staticmethod
    async def create(
        session: AsyncSession,
        run_type: str,
        source_name: str | None = None,
        config_json: dict | None = None,
    ) -> IngestionRun:
        """Insert a new run row in ``status='running'``.

        Flushes; does not commit. Caller controls the transaction lifecycle.

        ``config_json`` MUST NOT contain secrets (bot tokens, db passwords, env values).
        Treat it as policy metadata only — operator inputs and run parameters that are safe
        to dump in admin views.
        """
        if run_type not in _ALLOWED_RUN_TYPES:
            raise ValueError(
                f"unsupported run_type {run_type!r}; allowed: {sorted(_ALLOWED_RUN_TYPES)}"
            )

        run = IngestionRun(
            run_type=run_type,
            source_name=source_name,
            status="running",
            config_json=config_json,
        )
        session.add(run)
        await session.flush()
        return run

    @staticmethod
    async def update_status(
        session: AsyncSession,
        run: IngestionRun,
        status: str,
        stats_json: dict | None = None,
        error_json: dict | None = None,
    ) -> IngestionRun:
        """Set the run's status (and optionally stats/error). Sets ``finished_at`` to the
        current statement time when transitioning to a terminal status."""
        if status not in _ALLOWED_STATUSES:
            raise ValueError(
                f"unsupported status {status!r}; allowed: {sorted(_ALLOWED_STATUSES)}"
            )

        run.status = status
        if stats_json is not None:
            run.stats_json = stats_json
        if error_json is not None:
            run.error_json = error_json
        if status in _TERMINAL_STATUSES and run.finished_at is None:
            # Use Python clock here (not func.now) so the timestamp is set even if the
            # caller never flushes / commits to a real DB. Postgres column has timezone=True;
            # using UTC here keeps stored values consistent with server-default rows.
            run.finished_at = datetime.now(tz=timezone.utc)
        await session.flush()
        return run

    @staticmethod
    async def get_active_live(session: AsyncSession) -> IngestionRun | None:
        """Return the most-recent ``run_type='live'`` row in ``status='running'``, if any.

        The live-ingestion service uses this on bot startup to attach to an existing run
        (e.g., if the bot restarted mid-run) or, when None is returned, create a new one.
        """
        stmt = (
            select(IngestionRun)
            .where(
                IngestionRun.run_type == "live",
                IngestionRun.status == "running",
            )
            .order_by(IngestionRun.started_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
