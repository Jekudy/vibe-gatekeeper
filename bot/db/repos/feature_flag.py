"""Repository for ``feature_flags`` (T1-01).

The contract is intentionally minimal: ``get()`` returns a bool, defaulting to False for
missing flags. ``set_enabled()`` is provided as a small helper for tests, future admin UI,
and one-off SQL-equivalent operations from a Python REPL.

All ``memory.*`` flags default OFF until an explicit row toggles them on. The migration
does NOT seed any rows — see ``alembic/versions/003_add_feature_flags.py``.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import FeatureFlag


class FeatureFlagRepo:
    @staticmethod
    async def get(
        session: AsyncSession,
        flag_key: str,
        scope_type: str | None = None,
        scope_id: str | None = None,
    ) -> bool:
        """Return the boolean state of a flag. Missing flag → False.

        Resolution does NOT walk the scope hierarchy — callers ask for the scope they care
        about and get a direct yes/no. A future ``get_with_fallback()`` could implement
        scope-walk semantics if needed.
        """
        stmt = select(FeatureFlag.enabled).where(
            FeatureFlag.flag_key == flag_key,
            FeatureFlag.scope_type.is_(scope_type) if scope_type is None else FeatureFlag.scope_type == scope_type,
            FeatureFlag.scope_id.is_(scope_id) if scope_id is None else FeatureFlag.scope_id == scope_id,
        )
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        return bool(row) if row is not None else False

    @staticmethod
    async def set_enabled(
        session: AsyncSession,
        flag_key: str,
        enabled: bool,
        scope_type: str | None = None,
        scope_id: str | None = None,
        config_json: dict | None = None,
        updated_by: int | None = None,
    ) -> FeatureFlag:
        """Upsert a flag row by ``(flag_key, scope_type, scope_id)`` and set its state.

        Flushes; does not commit. Caller controls the transaction lifecycle. Postgres-only
        (uses ON CONFLICT). Conflict target is the unique constraint
        ``uq_feature_flags_key_scope``.
        """
        stmt = (
            pg_insert(FeatureFlag)
            .values(
                flag_key=flag_key,
                scope_type=scope_type,
                scope_id=scope_id,
                enabled=enabled,
                config_json=config_json,
                updated_by=updated_by,
            )
            .on_conflict_do_update(
                constraint="uq_feature_flags_key_scope",
                set_={
                    "enabled": enabled,
                    "config_json": config_json,
                    "updated_by": updated_by,
                },
            )
            .returning(FeatureFlag)
        )
        result = await session.execute(stmt)
        await session.flush()
        return result.scalar_one()
