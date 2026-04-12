# Vibe Gatekeeper Staging Cutover

Date: 2026-04-12

## What Is Already Ready

- Source of truth moved to GitHub:
  - `https://github.com/Jekudy/vibe-gatekeeper`
- CI is green.
- Release workflow pushes immutable bot/web images after successful CI.
- Coolify is installed and healthy on the VPS.
- Coolify localhost server bootstrap is fixed and onboarding is complete.
- Old production runtime remains untouched at:
  - `/home/claw/vibe-gatekeeper`

## Current Blocker

Coolify staging cannot pull the release images yet.

Observed facts on 2026-04-12:

- `gh run list` shows successful `CI` and successful `Release Images`.
- local `gh auth token` does not have `read:packages`
- `docker manifest inspect ghcr.io/jekudy/vibe-gatekeeper-bot:sha-f52919b` returns `denied`

Therefore staging in Coolify is blocked until one of the following is done:

- GHCR packages `vibe-gatekeeper-bot` and `vibe-gatekeeper-web` are made public
- a GitHub token with `read:packages` is added to Coolify registry credentials

## Staging Shape Once GHCR Pull Works

Create these resources in Coolify:

- one staging PostgreSQL instance
- one staging Redis instance
- one web app from `ghcr.io/jekudy/vibe-gatekeeper-web`
- one bot app from `ghcr.io/jekudy/vibe-gatekeeper-bot`

Use staging-only secrets:

- staging bot token
- staging DB DSN
- staging Redis DSN
- staging web password
- staging admin IDs if needed

## Smoke Checks

After the first successful staging deploy:

- bot process starts cleanly
- web login works
- DB schema init/migrations succeed
- Redis-backed runtime path works
- scheduler/background loop starts
- Google credentials path is mounted correctly if used

## Production Safety Rule

Do not point the production Telegram bot token at Coolify until staging has passed smoke checks.

The production bot uses Telegram polling, so the final cutover must still be a short stop/start window:

1. fresh DB backup
2. stop old prod bot
3. start new prod bot in Coolify
4. verify live message flow
