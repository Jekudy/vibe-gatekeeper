---
name: verify
description: Quick project health check for vibe-gatekeeper — git status, ruff lint, ruff format check, pytest, alembic heads, and docker-compose config. Read-only.
---

# verify

Fast end-to-end sanity check. Runs nothing mutating. Wrap each slow step with gtimeout.

## Steps

1. Git state:
   ```bash
   git branch --show-current
   git status --short
   ```

2. Lint (ruff):
   ```bash
   uvx ruff check . 2>&1 | tail -20
   ```
   Fallback if uvx unavailable: `ruff check .` (assumes `uv sync` has been run).

3. Format check (no rewrites):
   ```bash
   uvx ruff format --check . 2>&1 | tail -5
   ```

4. Pytest:
   ```bash
   gtimeout 120 uv run pytest -q 2>&1 | tail -40
   ```
   Fallback: `gtimeout 120 pytest -q 2>&1 | tail -40`.

5. Alembic head:
   ```bash
   uv run alembic heads 2>&1 | tail -5
   ```

6. docker-compose config:
   ```bash
   docker compose config --quiet && echo "docker-compose.yml OK" || echo "docker compose config FAILED"
   ```

7. GHCR image references (sanity):
   ```bash
   grep -E 'ghcr\.io/jekudy/vibe-gatekeeper-(bot|web)' .github/workflows/release.yml README.md docs/runbook.md 2>/dev/null | head -10
   ```

## Pass criteria

- `ruff check .` → 0 violations
- `ruff format --check .` → 0 would-reformat
- `pytest -q` → exits 0
- `alembic heads` → one head matching latest file in `alembic/versions/`
- `docker compose config --quiet` → exit 0
- GHCR refs consistent across workflow and docs

## Notes

- Read-only. Never runs `alembic upgrade`, `docker compose up`, or `ruff check --fix`.
- Does not touch the prod VPS / Coolify. Production verification lives in `docs/runbook.md`.
- If anything fails, surface the output — do not try to "fix" it inside this skill.

<!-- updated-by-superflow:2026-04-24 -->
