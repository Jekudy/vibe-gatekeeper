# Runbook

## Runtime Boundary

### Product Apps

These belong in Coolify:

- `vibe-gatekeeper`
- `foodzy`
- other normal app/web/bot/worker services

### Operator Services

These stay host-managed when they need direct VPS control:

- Telegram-based operator services
- watchdog services
- orchestration tools that need Docker, SSH, or unrestricted shell access

## Environment Model

### Local

- `DEV_MODE=true`
- separate dev bot token
- SQLite
- no shared production resources

### Staging

- `DEV_MODE=false`
- separate staging bot token
- separate staging DB
- separate staging Redis
- separate staging web password
- optional isolated staging chat

### Production

- `DEV_MODE=false`
- production bot token
- production DB
- production Redis
- production web password

## Secret Rules

Never commit:

- `.env`
- `.env.staging`
- `.env.production`
- `credentials.json`

## Release Model

- CI validates the repo.
- Release workflow builds and pushes GHCR images.
- Coolify deploys pre-built images from GHCR.
- Rollback uses the previous image tag.

## Current Server State

As of 2026-04-12:

- GitHub repo exists at `https://github.com/Jekudy/vibe-gatekeeper`.
- CI is green on `main`.
- Release workflow is gated on successful CI and pushes bot/web images to GHCR.
- Coolify is installed on the VPS in parallel to the old runtime.
- Coolify dashboard is intentionally bound to the Tailscale IP only:
  - `http://100.101.196.21:8100`
- The old production runtime is still alive:
  - path: `/home/claw/vibe-gatekeeper`
  - public web: `0.0.0.0:8080`

## Current Deployment Blocker

Coolify is ready, but staging deployment from GHCR is not finished yet because the current local GitHub CLI token does not have `read:packages`, and GHCR image pulls return `denied`.

One of these must be true before Coolify can deploy the `bot` and `web` images:

- GHCR packages are made public, or
- a GitHub token with `read:packages` is added to Coolify as registry credentials

This does not affect the already-working CI and image release path. It only blocks the final `Coolify -> pull from GHCR` step.

## Current Bootstrap Limitation

The old production runtime at `/home/claw/vibe-gatekeeper` remains the live user path until the new staging path is verified and a controlled bot cutover window is prepared.
