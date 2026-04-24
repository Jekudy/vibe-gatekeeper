# vibe-gatekeeper — Claude Instructions

## Project Overview

Telegram gatekeeper bot (aiogram 3) plus a FastAPI admin web surface for community onboarding: applications, vouching, intro refresh, member visibility. Python 3.12, SQLAlchemy 2 async over asyncpg/PostgreSQL, Redis for FSM in prod, APScheduler for periodic jobs, `gspread` (sync) for Google Sheets sync, Jinja2 + Bootstrap 5 CDN for web UI. All frameworks verified by import scan in `bot/` and `web/`.

## Layout

```
bot/          34 .py, ~2,700 LOC — Telegram bot (aiogram 3)
  __main__.py     entry: Bot + Dispatcher + middleware + 7 routers + scheduler
  handlers/       7 routers: start, questionnaire, vouch, admin, chat_events, forward_lookup, chat_messages
  db/models.py    SQLAlchemy 2 DeclarativeBase (148 LOC)
  db/repos/       6 repositories: user, application, questionnaire, vouch, intro, message
  services/       scheduler.py (229), sheets.py (431 — largest file), invite.py (47)
  middlewares/db_session.py   injects AsyncSession per aiogram update
  keyboards/ filters/ states/ texts.py
web/          14 files (9 .py + 4 .html + 1 .css), ~598 LOC — FastAPI admin
  app.py          create_app factory + HTTP auth middleware
  auth.py         WEB_PASSWORD compare + itsdangerous cookie signer
  routes/         auth, dashboard, members
  templates/      base, login, dashboard, members (Bootstrap 5 CDN, no build step)
alembic/      3 .py, 205 LOC — migrations; single revision in 001_initial.py
tests/        4 .py, 97 LOC — pytest collects 4 tests
docs/         runbook.md (authoritative ops), ops/, superpowers/plans+specs, superflow/
```

## Commands

```bash
# Install (README uses pip; uv binary is installed but no uv.lock committed)
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"            # dev extras: pytest, ruff

# Run
python -m bot                      # Telegram bot (long polling)
python -m web                      # FastAPI on 0.0.0.0:8080 via uvicorn

# Tests + lint (exactly what CI runs — see .github/workflows/ci.yml:37,40)
pytest -q                          # collects 4 tests from tests/ only
ruff check .                       # 0 violations as of 2026-04-24

# Format (NOT enforced in CI; 26/55 files would be reformatted)
ruff format --check .

# Migrations
alembic revision --autogenerate -m "describe change"
alembic upgrade head

# Docker
docker compose up                  # bot + web + postgres:16-alpine + redis:7-alpine
```

Prereqs: `DATABASE_URL`, `BOT_TOKEN`, `WEB_PASSWORD` and ~9 other env vars. See `.env.example` for the full 12-key list. In `DEV_MODE=true` the bot uses SQLite (`vibe_gatekeeper.db`) and `MemoryStorage` for FSM, so Redis and Postgres are not required locally.

## Environments

- **Local:** `DEV_MODE=true`, SQLite, in-memory FSM, separate dev bot token (`bot/__main__.py:34-39` + `bot/config.py`).
- **Staging:** `DEV_MODE=false`, separate bot token / DB / Redis / web password. Optional isolated chat. See `docs/runbook.md`.
- **Production:** `DEV_MODE=false`, prod bot token / DB / Redis / web password. Served from Coolify.

## Runtime status (post-cutover)

- **Prod cutover completed 2026-04-20.** `@vibeshkoder_bot` now runs under Coolify on the VPS (`187.77.98.73`, Coolify dashboard at Tailscale `100.101.196.21:8100`). See `docs/runbook.md:65-75, 106-117` for the full cutover log.
- **Legacy runtime at `/home/claw/vibe-gatekeeper` is stopped** (`docker compose down` on 2026-04-20). Files preserved for rollback; retention window ends ~2026-04-27 (7 days post-cutover per `docs/runbook.md:135`).
- **Coolify resources (prod, despite `-staging` suffix in names):** app `vibe-gatekeeper-web`, app `vibe-gatekeeper-bot-staging`, postgres `vibe-gatekeeper-pg-staging` (`postgres:15-alpine`), redis `vibe-gatekeeper-redis-staging` (`redis:7-alpine`). Names are cosmetic; rename later. Table at `docs/runbook.md:90-95`.
- **`credentials.json` is still mounted from the legacy host path** `/home/claw/vibe-gatekeeper/credentials.json` via `custom_docker_run_options` (`docs/runbook.md:104`). Tracked as P0 tech debt in `docs/superflow/project-health-report.md` — must move off legacy path before VPS cleanup.
- **Rollback procedure:** stop Coolify bot → stop Coolify web → `docker compose up -d` on legacy. Full steps in `docs/runbook.md:119-133`.
- **Release flow:** push to `main` → CI green → `.github/workflows/release.yml` builds both Dockerfiles and pushes `sha-<hash>` + `:main` to `ghcr.io/jekudy/vibe-gatekeeper-{bot,web}` → Coolify pulls `:main`.

## Known drift (keep in mind when reading docs)

- **`SPEC.md:283` (§7) is wrong** — describes a Telegram Login Widget + HMAC-SHA256 for web auth. Actual implementation is a password form + `itsdangerous.URLSafeTimedSerializer` cookie (`web/auth.py`, `web/routes/auth.py`). No Widget code exists.
- **`SPEC.md:75-78` (§1) is aspirational** — lists `test_questionnaire.py`, `test_vouch.py`, `test_sheets.py`, `test_scheduler.py`. None exist. Real tests: `tests/test_settings.py`, `tests/test_web_app.py`, `tests/test_web_auth.py`, `tests/conftest.py`.
- **`SPEC.md §1` structure diagram is outdated** — missing `bot/handlers/chat_events.py` and `bot/db/repos/intro.py`.
- **`README.md:30-36` + preflight mention `uv`** — `uv` binary is on PATH but `uv.lock` is absent and CI uses `pip install -e ".[dev]"` (`.github/workflows/ci.yml:34`). Treat pip as current truth.
- **Declared-but-unused deps** in `pyproject.toml:11,19,21`: `gspread-asyncio`, `httpx`, `python-dotenv` — zero imports in `bot/` or `web/`.
- **Top-level `test_*.py` + `phone_login.py` / `scan_work.py` / `transcribe_voice.py`** are Telethon ops scripts, not pytest targets (`pyproject.toml:42-44` pins `testpaths = ["tests"]`). Needs `[ops]` extra.

## Key rules

- **GitHub is the source of truth; the VPS is not.** All changes flow local → PR → merge → CI → GHCR → Coolify. SSH to the VPS is for logs/diagnostics only.
- **Never commit secrets.** `.env`, `.env.staging`, `.env.production`, `credentials.json` all gitignored; one live credential value already leaked into `docs/runbook.md:110` — rotate before the next commit touches that file (see `docs/superflow/project-health-report.md` P0 #1).
- **`web` depends on `bot`, never the reverse.** `web/config.py`, `web/routes/dashboard.py`, `web/routes/members.py` import from `bot.db` and `bot.config`. There is no shared `core/` package yet — be careful renaming anything under `bot/db/`.
- **Web routes currently open `async_session()` directly.** `web/routes/dashboard.py:18` and `web/routes/members.py:16` bypass the aiogram `DbSessionMiddleware`. Safe today because they are read-only. If you add a write endpoint, introduce a FastAPI DI session or you will skip commit/rollback.
- **DEV_MODE gates schema creation path.** `bot/__main__.py:22-29` calls `Base.metadata.create_all` when `DEV_MODE=true`; prod uses Alembic. Keep the models + migrations in sync manually.
- **Migrations are baked into the bot container command** (`Dockerfile.bot:14` → `alembic upgrade head && python -m bot`). A bad migration = boot loop — tracked as P1 tech debt.
- **All user-facing strings live in `bot/texts.py`** (133 LOC, Russian). Don't inline strings in handlers.
- **Language policy (per global CLAUDE.md):** code, comments, docs in English; user communication in Russian.

## Where to look first

- `docs/runbook.md` — **authoritative** current ops state, Coolify resources, cutover log, rollback.
- `docs/superflow/project-health-report.md` — **authoritative** tech-debt and security backlog (45 findings, 1 critical + 9 high). Read before planning any refactor.
- `SPEC.md` — product intent **with caveats** above. Use as a requirements hint, verify against code.
- `bot/__main__.py` + `web/app.py` — entry points; two-paragraph read to orient on any new task.
- `.github/workflows/ci.yml` + `release.yml` — authoritative on what checks run and how images ship.

## Known issues / tech debt (top items — full list in health report)

| Priority | Issue | Evidence |
|----------|-------|----------|
| P0 | `WEB_PASSWORD` value committed in runbook | `docs/runbook.md:110` |
| P0 | `credentials.json` still on legacy path past 7-day retention window | `docs/runbook.md:104` |
| P1 | Weak config defaults (`changeme`, `admin`) in `bot/config.py:10-19` | `bot/config.py` |
| P1 | Dockerfiles run as root | `Dockerfile.bot`, `Dockerfile.web` — no `USER` |
| P1 | Migration in bot CMD → boot-loop on bad revision | `Dockerfile.bot:14` |
| P1 | ~9% test coverage (4 tests / 48 source modules) | `tests/` |
| P1 | Session cookie missing `Secure` flag, prod served over HTTP | `web/routes/auth.py:37-43` |
| P2 | Formatter not enforced in CI (26/55 files would reformat) | `.github/workflows/ci.yml:40` |
| P2 | Hardcoded `@vibeshkoder_bot` in kick message ignores `WEB_BOT_USERNAME` | `bot/handlers/chat_events.py:119` |

<!-- updated-by-superflow:2026-04-24 -->
