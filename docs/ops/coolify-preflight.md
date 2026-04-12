# Coolify Preflight

Date: 2026-04-12

## Goal

Record the VPS facts that matter for a safe parallel Coolify install and later service migration.

## Access Model

- VPS is reachable from the operator machine over Tailscale.
- Tailscale IP:
  - `100.101.196.21`
- Coolify dashboard is intentionally bound to the Tailscale IP only:
  - `http://100.101.196.21:8100`

## Existing Service Inventory

### Product or app-like containers

- `foodzy-bot-1`
- `foodzy-postgres-1`
- `vibe-gatekeeper-bot-1`
- `vibe-gatekeeper-web-1`
- `vibe-gatekeeper-db-1`
- `vibe-gatekeeper-redis-1`

### Other containers currently on the host

- `fast-mcp-telegram`
- `vaultwarden`
- `vaultwarden-caddy`
- `vaultwarden-backup`
- `radicale`
- `caldav-sync`

### Host-managed services

- `claude-tg-watchdog.service`

## Port Inventory

Observed on 2026-04-12:

- `100.101.196.21:80` -> `vaultwarden-caddy`
- `100.101.196.21:443` -> `vaultwarden-caddy`
- `127.0.0.1:8000` -> `fast-mcp-telegram`
- `0.0.0.0:8080` -> `vibe-gatekeeper-web`
- `0.0.0.0:8443` -> `foodzy-bot-1`
- `0.0.0.0:5232` -> `radicale`
- `0.0.0.0:5432` -> `foodzy-postgres-1`
- `0.0.0.0:6001-6002` -> `coolify-realtime`

Implications:

- Coolify could not start on `127.0.0.1:8000` because `fast-mcp-telegram` already owned that port.
- Public `80/443` are not free in the general sense because `vaultwarden-caddy` already binds them on the Tailscale IP.
- The safest first step was to keep the Coolify admin UI off the public interface and bind it only to Tailscale.

## Coolify Bootstrap Notes

- Coolify core is running in parallel to the old app stacks.
- The initial install left the app container in `Created` because port `8000` was already allocated.
- The compose override was adjusted to bind Coolify to:
  - `100.101.196.21:8100:8080`
- Root admin bootstrap was completed on 2026-04-12.
- The localhost server bootstrap inside Coolify was repaired by:
  - generating a localhost SSH key
  - adding the public key to `root/.ssh/authorized_keys`
  - restoring `private_keys.id=0`
  - fixing `servers.id=0` to use `root`

## Management Boundary

### Move into Coolify

- `vibe-gatekeeper`
- `foodzy`
- future normal product services

### Keep host-managed

- watchdog and operator services
- Telegram-controlled admin services
- anything that needs unrestricted Docker, SSH, or shell access

## Remaining Risk

The current blocker for staging in Coolify is not the VPS anymore. It is GHCR pull access:

- CI pushes the images successfully.
- Coolify cannot pull them yet until GHCR packages are public or a `read:packages` token is provided.
