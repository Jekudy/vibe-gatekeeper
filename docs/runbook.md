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

As of 2026-04-20 (prod cutover completed):

- GitHub repo exists at `https://github.com/Jekudy/vibe-gatekeeper`.
- CI is green on `main`.
- Release workflow is gated on successful CI and pushes bot/web images to GHCR.
- Coolify dashboard on Tailscale IP only: `http://100.101.196.21:8100`.
- Public VPS IP: `187.77.98.73` (Hostinger srv1435593).
- **Production bot `@vibeshkoder_bot` is now running under Coolify** (Docker-managed via Coolify).
- Legacy runtime at `/home/claw/vibe-gatekeeper` was stopped and removed on 2026-04-20 via `docker compose down`.
- Public web: `0.0.0.0:8080` is now owned by the Coolify-managed web container.

## Coolify Registry & SSH (resolved 2026-04-19)

- GHCR pull is unblocked via `docker login ghcr.io -u Jekudy` on the VPS as root.
- Auth lives in `/root/.docker/config.json`.
- Coolify reuses the host Docker daemon, so no Coolify-side registry resource is needed.
- Coolify localhost server bootstrap was repaired again on 2026-04-19:
  - `servers.id=0` user reverted to `root`
  - Coolify localhost public key re-added to `/root/.ssh/authorized_keys`
  - server validation now reports `is_reachable=true`, `is_usable=true`

## Coolify Prod Resources

Initially created on 2026-04-19 as "staging" shells, repurposed as prod on 2026-04-20 after direct cutover (no staging phase; `DEV_MODE=false` on both apps). Names still carry `-staging` suffix — cosmetic, rename later. Coolify project: `My first project` / environment: `staging` (label, not runtime).

| Kind | UUID | Notes |
|---|---|---|
| App `vibe-gatekeeper-web` | `cexv50jspo5gl3kq6ojypw43` | image `ghcr.io/jekudy/vibe-gatekeeper-web:main`, port `8080:8080` (public), fqdn sslip `cexv50jspo5gl3kq6ojypw43.187.77.98.73.sslip.io` |
| App `vibe-gatekeeper-bot-staging` | `maiwn569gziz935wv0w7kcch` | image `ghcr.io/jekudy/vibe-gatekeeper-bot:main`, polling mode |
| Postgres `vibe-gatekeeper-pg-staging` | `hdazvm5fz836xj9mdyn8c629` | `postgres:15-alpine`, db `vibe_gatekeeper`, user `vibe`, data migrated from legacy on 2026-04-20 |
| Redis `vibe-gatekeeper-redis-staging` | `gl28f0g5exzzo4k8w0auzygk` | `redis:7-alpine`, password set |

Internal connection strings:

- `DATABASE_URL=postgresql+asyncpg://vibe:<DB_PW>@hdazvm5fz836xj9mdyn8c629:5432/vibe_gatekeeper`
- `REDIS_URL=redis://default:<REDIS_PW>@gl28f0g5exzzo4k8w0auzygk:6379/0`

DB / Redis / web passwords are stored in Coolify env vars only. API token in `~/.env.tokens:COOLIFY_API_TOKEN`.

Both apps use `custom_docker_run_options = -v /home/claw/vibe-gatekeeper/credentials.json:/app/credentials.json:ro` to mount Google service account credentials from the legacy directory (file preserved, not deleted).

> Note: secret values (tokens, passwords, signed keys) are redacted in this document. Actual values live only in Coolify env vars and local `.env` files. Never commit secret values to this file.

## Prod Cutover — 2026-04-20

Executed directly from legacy → Coolify prod (staging skipped, per user direction to work with prod only).

1. Cleaned Coolify env vars: deleted all `is_preview=true` duplicates; set runtime vars (`BOT_TOKEN`, `COMMUNITY_CHAT_ID=-1002716490518`, `ADMIN_IDS=[149820031]`, `GOOGLE_SHEET_ID`, `WEB_BASE_URL=http://187.77.98.73:8080`, `WEB_BOT_USERNAME=vibeshkoder_bot`, `WEB_PASSWORD=<managed in Coolify env — not committed>`, `DEV_MODE=false`) sourced from legacy `/home/claw/vibe-gatekeeper/.env`.
2. Mounted `credentials.json` into both apps via `custom_docker_run_options`.
3. Dumped legacy DB (`vibe-gatekeeper-db-1` → `pg_dump --clean --if-exists`) and restored into Coolify postgres. Row counts post-restore: users=275, applications=58, intros=44, vouch_log=39, questionnaire_answers=340, chat_messages=3109, alembic_version=1.
4. Stopped legacy bot first (Telegram session release), made a final incremental dump + restore to capture delta.
5. `docker compose down` on legacy — port 8080 and BOT_TOKEN both free.
6. PATCHed Coolify web `ports_mappings: 18080:8080 → 8080:8080` and redeployed.
7. Deployed Coolify bot for the first time.
8. Verified: `curl http://187.77.98.73:8080 → 302`, bot logs show `Run polling for bot @vibeshkoder_bot id=8271790115 - 'Shkoder'`, scheduler jobs registered (`check_vouch_deadlines`, `check_intro_refresh`, `sync_google_sheets`), real chat updates being handled within 500ms of start.

## Rollback Procedure

If Coolify prod becomes unhealthy:

```bash
ssh claw@187.77.98.73
TOKEN=<coolify api token>
API=http://100.101.196.21:8100/api/v1
# 1. Stop Coolify bot FIRST to release BOT_TOKEN from Telegram session:
curl -X POST -H "Authorization: Bearer $TOKEN" "$API/applications/maiwn569gziz935wv0w7kcch/stop"
# 2. Stop Coolify web to free port 8080:
curl -X POST -H "Authorization: Bearer $TOKEN" "$API/applications/cexv50jspo5gl3kq6ojypw43/stop"
# 3. Restart legacy stack:
cd /home/claw/vibe-gatekeeper && docker compose up -d
```

Legacy `docker-compose.yml`, `.env`, and `credentials.json` are preserved in `/home/claw/vibe-gatekeeper` — do not delete until prod has run stably for 7+ days.
