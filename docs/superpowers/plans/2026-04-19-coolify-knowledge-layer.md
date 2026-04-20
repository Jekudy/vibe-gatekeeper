# Coolify Knowledge Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the three-artefact Coolify knowledge layer (canonical playbook, `coolify-deploy` skill, `ag-mechanic` Coolify-first policy) plus project scaffolds, handoff document, and `verified_on` enforcement so future Coolify migrations follow one canonical procedure.

**Architecture:** Playbook owns knowledge, skill owns triggers and call order, agent owns default behavior. Project docs own filled-in parameter values. A living `Recommendations & Lessons Learned` section accumulates experience from every migration. A vault-level wrapper script enforces `verified_on` markers.

**Tech Stack:** Markdown (Obsidian vault, git repos), Claude Code plugins (plugin.json / marketplace.json), bash (enforcement script), no runtime code.

**Source of truth:** `~/Vibe/products/shkoderbot/docs/superpowers/specs/2026-04-19-coolify-knowledge-layer-design.md` (commit `285b364`). Every task below references spec sections by anchor; do not invent content.

---

## File Structure

**New files:**

- `~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md` — canonical playbook.
- `~/.claude/local-plugins/nocoders-agency/skills/coolify-deploy/SKILL.md` — operational skill.
- `~/Vibe/products/shkoderbot/docs/ops/ghcr-registry-access.md` — GHCR PAT scaffold.
- `~/Vibe/products/shkoderbot/docs/ops/vibe-gatekeeper-prod-cutover.md` — prod cutover scaffold.
- `~/Vibe/products/shkoderbot/docs/superpowers/handoffs/2026-04-19-coolify-bc-handoff.md` — B+C handoff.
- `~/Vibe/scripts/check-verified-on.sh` — `verified_on` enforcement wrapper script.
- `~/Vibe/scripts/test-check-verified-on.sh` — failing-case test for the script.

**Modified files:**

- `~/.claude/agents/ag-mechanic.md` — Coolify-first policy, anchor-citation rule, Recommended-services reorder.
- `~/.claude/local-plugins/nocoders-agency/.claude-plugin/plugin.json` — version bump `2.5.0 → 2.6.0`.
- `~/.claude/local-plugins/nocoders-agency/.claude-plugin/marketplace.json` — version bump `2.5.0 → 2.6.0`.
- `~/Vibe/products/shkoderbot/docs/runbook.md` — `Coolify deploys` section, `Known Issues & Quirks` section.

**Do not touch:**

- `~/Vibe/products/shkoderbot/docs/ops/coolify-preflight.md` — pre-existing input.
- `~/Vibe/products/shkoderbot/docs/ops/vibe-gatekeeper-staging-cutover.md` — pre-existing input.

---

## Pre-Flight

- [ ] **Step 0.1: Verify spec is current**

Run: `git -C ~/Vibe/products/shkoderbot log -1 --pretty=format:'%h %s' docs/superpowers/specs/2026-04-19-coolify-knowledge-layer-design.md`
Expected: returns `285b364 docs: add coolify knowledge-layer design spec ...` (or a later commit that still leaves the spec intact).

- [ ] **Step 0.2: Confirm marketplace + plugin names for skill release**

Run: `jq -r '.plugins[0].name, .name' ~/.claude/local-plugins/nocoders-agency/.claude-plugin/marketplace.json`
Expected: `nocoders-agency` on line 1, `nocoders-agency-marketplace` on line 2. These feed the `claude plugin update` command used later.

---

## Task 1: Create playbook skeleton with header and section stubs

**Files:**
- Create: `~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md`

- [ ] **Step 1.1: Create the file with header and section stubs**

Create the file with exactly this content:

```markdown
# Coolify Deploy Playbook

STATUS: UNVERIFIED DRAFT
Coolify version tested: none
Last validated against: never
Canonical anchors: overview, p0, p0.1, p1, p2, p3, p3.5, p4, p5, p6, p7, p8, p9, p10, p11, recommendations

# Overview

verified_on: never

<to be filled in Task 2>

# p0 — Prereq & network topology

verified_on: never

<to be filled in Task 3>

# p0.1 — Vaultwarden cutover sub-procedure

verified_on: never

<to be filled in Task 3>

# p1 — GHCR pull

verified_on: never

<to be filled in Task 4>

# p2 — New app from GHCR

verified_on: never

<to be filled in Task 5>

# p3 — Database services

verified_on: never

<to be filled in Task 6>

# p3.5 — Persistent volumes & backup

verified_on: never

<to be filled in Task 6>

# p4 — Healthcheck & polling-conflict detection

verified_on: never

<to be filled in Task 7>

# p5 — Smoke checks

verified_on: never

<to be filled in Task 8>

# p6 — Cutover & rollback as executable runbook

verified_on: never

<to be filled in Task 9>

# p7 — Legacy cleanup

verified_on: never

<to be filled in Task 10>

# p8 — Disk & IOPS precheck for dual-stack window

verified_on: never

<to be filled in Task 11>

# p9 — Observability baseline

verified_on: never

<to be filled in Task 12>

# p10 — Secrets & access hygiene

verified_on: never

<to be filled in Task 13>

# p11 — Troubleshooting table

verified_on: never

<to be filled in Task 14>

# Recommendations & Lessons Learned

Append-only. Each migration adds 1–3 entries in the template below.

```

- [ ] **Step 1.2: Commit**

```bash
cd ~/Vibe
git add knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md
git commit -m "docs(coolify-playbook): scaffold canonical deploy playbook with section stubs"
```

Note: if `~/Vibe/` is not a git repository, skip the commit and instead run `ls -la ~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md` to confirm the file exists. The CI enforcement in Task 21 handles the non-git case.

---

## Task 2: Write Overview section

**Files:**
- Modify: `~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md` (Overview section only)

- [ ] **Step 2.1: Replace Overview stub with full content**

Overview must cover (per spec `Playbook Content Specification`):

- The Git → GHCR → Coolify flow in one diagram or numbered list.
- What Coolify owns (product apps, databases, Traefik, secrets UI) vs what stays host-managed (watchdog, systemd operator services, anything needing raw Docker socket access).
- Coolify-first default rationale for single-VPS products.
- **Coolify exit strategy**: portable primitives (GHCR immutable images, Dockerfile, env contracts, `pg_dump` / `pg_restore` backups, age/sops-encrypted state archives) vs Coolify-specific parts (webhook receiver, Traefik label conventions, Coolify secrets DB layout). Exit means: the portable primitives continue to work on Dokploy/Kamal/plain-compose; the Coolify-specific parts are re-implemented.

Do not leave Coolify version blank in the body — state explicitly "this Overview is written against Coolify <version from current VPS>; when the tested version changes, revisit this section".

- [ ] **Step 2.2: Commit**

```bash
cd ~/Vibe
git add knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md
git commit -m "docs(coolify-playbook): write Overview — flow, ownership, exit strategy"
```

---

## Task 3: Write p0 (network topology) and p0.1 (vaultwarden cutover)

**Files:**
- Modify: `~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md`

- [ ] **Step 3.1: Replace p0 stub**

Per spec: VPS inventory, port usage, Tailscale posture, proxy strategy decision tree with **all three paths written as full procedures**:

1. Migrate vaultwarden into Coolify — body points to `p0.1`.
2. Remove vaultwarden — document `bw export` / server admin panel export, decommission, DNS cleanup.
3. Coolify Traefik on alt-port `8080/8443`, front caddy proxies to it — include an example caddy block and Coolify Traefik label overrides, note two-proxy monitoring tech-debt.

Also cover:
- `claude-tg-watchdog` interaction: watchdog only monitors host-level services, never Coolify-managed apps.
- Coolify webhook receiver security: Tailscale-only binding by default; if public, protect with shared secret + IP allowlist.
- Explicit recommendation line: "default for single-tenant single-VPS setups is path 1 (migrate vaultwarden into Coolify); Spec B records the final choice".

- [ ] **Step 3.2: Replace p0.1 stub with the 7-step sub-procedure**

Copy the seven numbered steps verbatim from spec section `p0.1`:

1. Announce maintenance window; lock new registrations.
2. Dump vaultwarden data: copy `/data/db.sqlite3` + `/data/attachments/` + `/data/config.json` to a staging dir; verify checksums.
3. Stop legacy vaultwarden + caddy; free ports `80/443`.
4. Deploy vaultwarden as a Coolify app (`vaultwarden/server` pinned by digest, Traefik labels for admin FQDN, Coolify-managed Let's Encrypt).
5. Restore dump into Coolify-managed volume at `/data`.
6. Smoke: web login, known-password retrieval on secondary client, WebSocket sync.
7. Rollback: stop Coolify vaultwarden app, restore caddy + legacy container, re-bind `80/443`, revert DNS if changed.

- [ ] **Step 3.3: Commit**

```bash
cd ~/Vibe
git add knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md
git commit -m "docs(coolify-playbook): write p0 topology + p0.1 vaultwarden cutover"
```

---

## Task 4: Write p1 (GHCR pull — two mechanisms)

**Files:**
- Modify: `~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md`

- [ ] **Step 4.1: Replace p1 stub**

Document two equally valid mechanisms per spec `Decisions` and `p1`:

1. **Host-level `docker login`** (recommended single-tenant single-owner VPS). Command: `docker login ghcr.io -u <owner>` as root. Credentials path: `/root/.docker/config.json`. Coolify reuses host Docker daemon. Pros: simplest; one auth for all apps. Cons: shared across apps; rotation touches everything.
2. **Coolify Registry Credentials** (multi-tenant or multi-registry). Fine-grained Owner PAT with `read:packages` added via Coolify UI → Sources → Registries. Blue/green rotation: keep two active PATs during the cutover week, retire the older one. Pros: per-credential isolation, Coolify-native UI, supports multiple registries. Cons: extra resource, more click-ops.

Common to both:
- PAT scope: `read:packages` only.
- Expiry: 90 days.
- Calendar alerts: 14 / 7 / 1 day before expiry.
- Digest pinning: always use `ghcr.io/<owner>/<image>@sha256:<digest>`, never `:latest` or branch tags in production.
- Selection heuristic: "one VPS + one owner + no compliance audit requirement" → mechanism 1; otherwise mechanism 2.

Also include fallback registry note: local self-hosted registry on same VPS as disaster cache; flagged as future work in Open Items.

- [ ] **Step 4.2: Commit**

```bash
cd ~/Vibe
git add knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md
git commit -m "docs(coolify-playbook): write p1 GHCR pull with two mechanisms"
```

---

## Task 5: Write p2 (New app from GHCR)

**Files:**
- Modify: `~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md`

- [ ] **Step 5.1: Replace p2 stub**

Cover per spec:

- App creation in Coolify UI (project → environment → new resource → Docker Image).
- Image reference: digest-pinned per `p1`.
- Env wiring (Coolify env panel), volumes, CPU/RAM resource limits (defaults for Python bot: 512M RAM soft limit, 1 CPU).
- Coolify `depends_on`-equivalent: apps grouped under the same project + environment start in roughly creation order, but Coolify does NOT guarantee DB readiness at container start. A wait-for-it retry loop in the bot entrypoint is mandatory.
- **Alembic migration execution model**: three options documented (init-container, entrypoint, Coolify pre-deploy command). Spec B pins one based on what the Coolify version supports. Default choice = entrypoint with `alembic upgrade head` before the bot boot.
- **Advisory lock for concurrent migration runs**: even though the bot is currently single-replica, the migration step wraps in `SELECT pg_advisory_lock(<stable-int>)` ... `pg_advisory_unlock(...)`. This prevents future multi-replica races.
- **Migration rollback policy**: forward-fix by default; downgrade path only where Alembic downgrade script is tested. Pre-migration DB snapshot is mandatory (`pg_dump` to a labeled file before `upgrade head`).
- Coolify webhook endpoint security: shared secret + IP allowlist if exposed publicly.

- [ ] **Step 5.2: Commit**

```bash
cd ~/Vibe
git add knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md
git commit -m "docs(coolify-playbook): write p2 app creation with migration model"
```

---

## Task 6: Write p3 (Database services) and p3.5 (Volumes & backup)

**Files:**
- Modify: `~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md`

- [ ] **Step 6.1: Replace p3 stub**

Managed Postgres + Redis in Coolify. Cover:
- Create Postgres service, point bot `DATABASE_URL` to `postgresql+asyncpg://<user>:<pw>@<uuid>:5432/<db>` (UUID is Coolify's internal container name).
- Create Redis service, point bot `REDIS_URL` to `redis://default:<pw>@<uuid>:6379/0`.
- **Redis state transfer options** (prod cutover): (a) drain pending flows by pausing new apply intake for 24h, (b) copy RDB with `redis-cli --rdb /tmp/dump.rdb`, (c) accept data loss with user announcement. Spec B records the chosen path.
- Restore drill procedure: create a throwaway copy of the service, restore backup, run a read query, destroy.

- [ ] **Step 6.2: Replace p3.5 stub**

Persistent volumes & backup:
- Explicit mount paths for all services; document Coolify's volume storage location on host (`/data/coolify/services/<uuid>/`).
- Backup cron: Coolify's built-in S3/local backup toggle. Enable for every DB service. Retention: 14 daily + 4 weekly.
- **Encrypt Coolify backups** with age or sops; key stored outside the backup destination (local keychain or separate S3 bucket with different credentials).
- Restore drill: monthly, to a staging service.
- **Google credentials mounted as file** at `/app/credentials.json` with mode `0400`, owner = container uid. Do NOT put the JSON content in env.
- Exclude Google credentials volume from Coolify backup scope; keep a separate sealed secret.

- [ ] **Step 6.3: Commit**

```bash
cd ~/Vibe
git add knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md
git commit -m "docs(coolify-playbook): write p3 DB services + p3.5 volumes & backup"
```

---

## Task 7: Write p4 (Healthcheck & polling-conflict detection)

**Files:**
- Modify: `~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md`

- [ ] **Step 7.1: Replace p4 stub**

Cover:
- Deep healthcheck endpoint specification: HTTP 200 on `/health` when all three hold — polling loop alive (last poll < 30s ago), DB ping OK, Redis ping OK.
- Coolify healthcheck interval pinned to 30 seconds. Consecutive-fail threshold = 3. Rollback trigger window = 90 seconds from the first failure.
- External uptime: healthchecks.io cron ping from inside the bot every 5 minutes. TG alert wiring to admin chat.
- **Active detection of Telegram 409 Conflict**: the bot logs `error_code: 409 Conflict` with a distinct template (`POLL_CONFLICT_409`); a Coolify log filter routes that template to a separate TG alert with `[POLLING CONFLICT]` subject.
- Pre-cutover `getUpdates` probe: before starting the new app, call `https://api.telegram.org/bot<TOKEN>/getUpdates?offset=-1` once and confirm the response is not `409`. If it is `409`, another runtime still holds the token — abort cutover.

- [ ] **Step 7.2: Commit**

```bash
cd ~/Vibe
git add knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md
git commit -m "docs(coolify-playbook): write p4 healthcheck + 409 polling detection"
```

---

## Task 8: Write p5 (Smoke checks)

**Files:**
- Modify: `~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md`

- [ ] **Step 8.1: Replace p5 stub**

Smoke check list in this order:
1. Infra checks: bot process up, web login OK, DB migrations applied, Redis connectable, scheduler loop started, Google credentials file present at expected path.
2. Log retention verification pre-cutover: confirm Coolify's default log retention is ≥ legacy journald retention; if shorter, increase before cutover so incident logs survive.
3. Log access procedure (grabbed **before** any rollback): `coolify logs <app-uuid> --tail 500 --follow` (primary); `docker logs <container-id> --tail 500` (fallback); `journalctl -u docker -f` (kernel-side).
4. Scripted product-specific happy-path E2E. Example for `vibe-gatekeeper`: send an apply intent from a test account → vouch from another test account → admin approves → member receives the invite. Generalize the template so foodzy can write its own E2E without copy-pasting.

- [ ] **Step 8.2: Commit**

```bash
cd ~/Vibe
git add knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md
git commit -m "docs(coolify-playbook): write p5 smoke checks with E2E template"
```

---

## Task 9: Write p6 (Cutover & rollback as executable runbook)

**Files:**
- Modify: `~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md`

- [ ] **Step 9.1: Replace p6 stub**

Cover:
- Measured cutover timing budget: Spec B writes the actual `stop-legacy → start-new → first-poll-resumed` duration observed on staging. Treat that number × 2 as the hard budget for prod.
- Hard startup timeout: 60 seconds. If new app does not reach healthy state within 60s, trigger rollback.
- SLI-based rollback triggers within the 5-minute window after start:
  - polling lag > 30 seconds (measured from last `getUpdates` response);
  - error rate > 5% (any non-200 in bot's outbound Telegram calls);
  - healthcheck fails 3 times in a row (90 seconds — see `p4`).
- **Executable rollback runbook** (numbered, exact shell commands where possible; treat as a runbook, not a description):

  ```
  1. STOP new app:        coolify stop <bot-uuid>
  2. Capture logs:        coolify logs <bot-uuid> --tail 1000 > /tmp/cutover-failure-$(date +%s).log
  3. Revert token if we rotated it: update BOT_TOKEN env in legacy compose .env file
  4. Start legacy:        cd /home/claw/vibe-gatekeeper && docker compose up -d
  5. Verify polling:      curl -s https://api.telegram.org/bot$TOKEN/getUpdates | jq '.ok'  # expect true, no 409
  6. Post-mortem snapshot: tar czf /root/cutover-forensic-$(date +%s).tar.gz /tmp/cutover-failure-*.log /home/claw/vibe-gatekeeper/.env /data/coolify/services/<bot-uuid>/
  ```

- **Lock mechanism** preventing accidental `docker compose up` on legacy during cutover window: temporarily rename the legacy compose file (`mv /home/claw/vibe-gatekeeper/docker-compose.yml docker-compose.yml.locked-during-cutover`) and restore it only if rollback is triggered. This prevents human error and shell-history replay.
- Pre-cutover `getUpdates` probe proving no other runtime currently holds the token (see `p4`).

- [ ] **Step 9.2: Commit**

```bash
cd ~/Vibe
git add knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md
git commit -m "docs(coolify-playbook): write p6 cutover & rollback executable runbook"
```

---

## Task 10: Write p7 (Legacy cleanup)

**Files:**
- Modify: `~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md`

- [ ] **Step 10.1: Replace p7 stub**

Cover:
- **Secret rotation list (mandatory BEFORE any file cleanup)**: bot token, DB password, Redis password if any, Google service-account key, GHCR PAT, webhook secrets, admin web password, session secrets. Rotate each, update new Coolify env, redeploy affected apps, verify, only then proceed to cleanup.
- **Shred with FS-specific caveats**: `shred -u` cannot guarantee erasure on journaling filesystems (ext4 / btrfs / zfs — all realistic on this VPS). Spec B writes the actual VPS filesystem and picks one path:
  - (a) overwrite-then-unlink (`shred -zu <file> && fstrim -v /`);
  - (b) rely on full-disk encryption if present;
  - (c) wipe the owning volume entirely.
- `swapoff -a && swapon -a` to flush swap residue that may contain token strings.
- journald purge of lines containing the rotated tokens: `journalctl --vacuum-time=1s` after rotation (coarse), or targeted deletion (finer but FS-level manipulation).
- Archive retention window: 72 hours from cutover. During this window the legacy compose must remain start-able within 5 minutes (see contract below).
- **Legacy-kept-warm contract**: during 72h, legacy compose must start-able in ≤ 5 min. Verification checkpoints at T+24h and T+48h: unlock compose, dry-run `docker compose up -d --no-start`, re-lock. Log each verification.
- After 72h + 0 incidents: delete the archive (shred per FS path above, remove volume directories, re-run `fstrim`).

- [ ] **Step 10.2: Commit**

```bash
cd ~/Vibe
git add knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md
git commit -m "docs(coolify-playbook): write p7 legacy cleanup with rotation list"
```

---

## Task 11: Write p8 (Disk & IOPS precheck)

**Files:**
- Modify: `~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md`

- [ ] **Step 11.1: Replace p8 stub**

Cover:
- Snapshot check: `df -h /` — require free ≥ 20 GB before cutover.
- 7-day disk-growth trend check: `du -s /data /home /var/lib/docker | tee /tmp/disk-$(date +%F).log` once per day for a week; inspect the trend, refuse cutover if growth > 1 GB/day without a known cause.
- IO wait: `iostat -x 2 5 | awk '/avg-cpu/{getline; print $4}'` — require average `%iowait` < 20%.
- Thresholds that block cutover:
  - free < 20 GB;
  - trend > 1 GB/day unexplained;
  - iowait > 20%.

- [ ] **Step 11.2: Commit**

```bash
cd ~/Vibe
git add knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md
git commit -m "docs(coolify-playbook): write p8 disk & IOPS precheck"
```

---

## Task 12: Write p9 (Observability baseline)

**Files:**
- Modify: `~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md`

- [ ] **Step 12.1: Replace p9 stub**

Cover:
- Healthchecks.io cron ping from inside the bot every 5 minutes. TG alert in admin chat when ping missed.
- **Required alerts (not optional)**:
  - error-rate alert: Sentry event count > 5/min → TG;
  - disk-free alert: `df /` < 10 GB → TG;
  - OOM-kill alert: `dmesg | grep -i oom-kill` in last 5 min → TG;
  - Traefik 5xx rate alert: if Coolify exposes Traefik metrics → TG when 5xx > 1% of requests over 5 min.
- Sentry DSN wired in bot env as the default structured-error path for production (not optional).
- **Note on single-vendor SPOF**: healthchecks.io is the only external observer in the baseline. Open Item tracks secondary-observer decision (UptimeRobot / Pingdom / second healthchecks.io project on different provider).

- [ ] **Step 12.2: Commit**

```bash
cd ~/Vibe
git add knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md
git commit -m "docs(coolify-playbook): write p9 observability baseline with required alerts"
```

---

## Task 13: Write p10 (Secrets & access hygiene)

**Files:**
- Modify: `~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md`

- [ ] **Step 13.1: Replace p10 stub**

Cover:
- Coolify secret storage: on disk at `/data/coolify/...` with ACL `600 root:root`; plaintext on FS even though masked in UI.
- RBAC in Coolify: create a separate operator account without "reveal secret" permission for day-to-day work; only the owner account has reveal.
- Tailscale break-glass as **first-class flow, not emergency-only**:
  - Scenario: Tailnet down or Tailscale control plane unreachable.
  - Procedure: direct SSH from a host whose public key is in `/root/.ssh/authorized_keys`; firewall rule allowlisting the admin's current IP for port 22; `ssh root@<vps-public-ip>`; Coolify UI reachable via SSH port-forward (`ssh -L 8100:localhost:8100 root@<ip>`).
  - Recovery: once Tailnet returns, remove the temporary firewall rule.
- Screenshot discipline: runbook explicitly asks operators never to screenshot Coolify UI pages showing revealed secrets.

- [ ] **Step 13.2: Commit**

```bash
cd ~/Vibe
git add knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md
git commit -m "docs(coolify-playbook): write p10 secrets hygiene + Tailscale break-glass"
```

---

## Task 14: Write p11 (Troubleshooting table)

**Files:**
- Modify: `~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md`

- [ ] **Step 14.1: Replace p11 stub**

Write a table with at least these 8 entries. Each row: Symptom, Likely cause, Exact diagnostic command, Exact fix.

1. `denied` / `unauthorized` on GHCR pull — PAT expired or wrong scope — `docker pull <image>` — re-login or update Coolify Registry Credentials.
2. Port conflict on app boot — another container holds the port — `docker ps --format '{{.Ports}} {{.Names}}' | grep <port>` — free the port or move the new app to an alt port.
3. DB DSN mismatch — wrong UUID or auth — `psql "$DATABASE_URL" -c '\dt'` — inspect Coolify service UUID and credentials.
4. Volume permission denied — container uid mismatch — `docker exec <id> ls -la /path` — chown on host or fix container uid.
5. Coolify Traefik not binding 80/443 — another service owns the port — `ss -ltnp '( sport = :80 or sport = :443 )'` — stop conflicting service or move Coolify Traefik to alt port.
6. Admin UI unreachable — Tailnet down or Coolify agent crashed — `tailscale status` then `docker ps | grep coolify` — Tailscale break-glass path (p10) or restart Coolify agent.
7. Healthcheck flapping — endpoint too strict or DB slow-start — `curl -v http://<host>:<port>/health` — loosen healthcheck (e.g., separate liveness vs readiness) or add wait-for-it retry.
8. **Coolify self-failure mode** — Coolify agent / proxy crashed but product containers still run — `docker ps | grep <app>` (containers visible; Coolify UI not) — Coolify itself has no external watchdog; restart Coolify stack: `cd /data/coolify && docker compose up -d`; product bot keeps running during the restart.

- [ ] **Step 14.2: Commit**

```bash
cd ~/Vibe
git add knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md
git commit -m "docs(coolify-playbook): write p11 troubleshooting table"
```

---

## Task 15: Finalize Recommendations & Lessons Learned template

**Files:**
- Modify: `~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md`

- [ ] **Step 15.1: Replace Recommendations stub with template and bootstrap entry**

Replace the closing section with exactly:

```markdown
# Recommendations & Lessons Learned

Append-only. Every migration or significant Coolify work adds 1–3 entries using the template below. Corrections go as new entries with back-references; do not edit prior entries.

## Entry template

```
## <YYYY-MM-DD> — <short title>
Context: <what we were doing>
Lesson: <what we learned / what worked / what did not>
Playbook impact: <which sections updated, or "no change">
```

## 2026-04-19 — Host-level `docker login` chosen for shkoderbot GHCR pull

Context: initial Coolify cutover for vibe-gatekeeper bot and web apps.
Lesson: Coolify reuses the host Docker daemon, so `docker login ghcr.io -u <owner>` as root on the VPS is enough — no Coolify-side Registry Credential needed for single-tenant setups. Simpler than PAT-in-Coolify for this scale.
Playbook impact: `p1` documents both mechanisms with "when to use which" guidance; this entry is the reasoning record.
```

- [ ] **Step 15.2: Commit**

```bash
cd ~/Vibe
git add knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md
git commit -m "docs(coolify-playbook): add Recommendations section with bootstrap entry"
```

---

## Task 16: Create `coolify-deploy` skill and bump plugin version

**Files:**
- Create: `~/.claude/local-plugins/nocoders-agency/skills/coolify-deploy/SKILL.md`
- Modify: `~/.claude/local-plugins/nocoders-agency/.claude-plugin/plugin.json`
- Modify: `~/.claude/local-plugins/nocoders-agency/.claude-plugin/marketplace.json`

- [ ] **Step 16.1: Create skill directory and SKILL.md**

Create `~/.claude/local-plugins/nocoders-agency/skills/coolify-deploy/SKILL.md` with the strict structure from spec `Skill Specification`:

```markdown
---
name: coolify-deploy
description: "Skill для настройки Coolify-деплоя из Git через GHCR. Триггеры: 'задеплой в coolify', 'перенеси сервис в coolify', 'настрой ghcr pull в coolify', 'подключи кулифай к репе'."
version: 1.0.0
---

## When to use / when NOT

Используй когда:
- запрос про первичный деплой сервиса в Coolify;
- нужно разобраться с GHCR pull в Coolify;
- миграция существующего сервиса с docker-compose в Coolify.

НЕ используй для:
- отладки упавшего прод-Coolify — это `coolify-debug` (namespace reserved);
- отката — это `coolify-rollback` (namespace reserved);
- вопросов "что такое Coolify" — отвечай без skill.

## Prerequisites

- VPS с Coolify (проверь `docs/ops/coolify-preflight.md` в проекте или `ssh <vps> 'docker ps | grep coolify'`).
- `gh` CLI authenticated.
- Dockerfile в repo.
- GHCR images build by CI.
- Playbook доступен по канонической ссылке.

## Call order

Anchor references only — все шаги живут в playbook:

1. `playbook#p1--ghcr-pull`
2. `playbook#p2--new-app-from-ghcr`
3. `playbook#p3--database-services`
4. `playbook#p35--persistent-volumes--backup`
5. `playbook#p4--healthcheck--polling-conflict-detection`
6. `playbook#p5--smoke-checks`
7. `playbook#p6--cutover--rollback-as-executable-runbook` (только при миграции существующего сервиса)

Опциональное продолжение: `playbook#p7--legacy-cleanup`.

## Parameter slot template

Слоты, которые caller заполняет в project docs (значения — НЕ здесь):

- `IMAGE_NAME`
- `IMAGE_DIGEST`
- `DOMAIN`
- `ENV_KEYS`
- `DB_DSN_SHAPE`
- `BOT_TOKEN_VAR`
- `GOOGLE_CREDS_MOUNT_PATH`

## Troubleshooting

See `playbook#p11--troubleshooting-table`.

## Recommendations

See `playbook#recommendations--lessons-learned`.

## Link

Canonical playbook: `~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md`.
```

- [ ] **Step 16.2: Bump plugin.json version**

Modify `~/.claude/local-plugins/nocoders-agency/.claude-plugin/plugin.json`:

```diff
-  "version": "2.5.0",
+  "version": "2.6.0",
```

Also update the top-level `description` field to mention the new skill — append `, coolify-deploy` (adjust exact text to match existing style).

- [ ] **Step 16.3: Bump marketplace.json version**

Modify `~/.claude/local-plugins/nocoders-agency/.claude-plugin/marketplace.json`:

```diff
-      "version": "2.5.0",
+      "version": "2.6.0",
```

- [ ] **Step 16.4: Refresh plugin cache**

Run: `claude plugin update "nocoders-agency@nocoders-agency-marketplace"`
Expected: command completes without error.

- [ ] **Step 16.5: Commit**

```bash
cd ~/.claude
git add local-plugins/nocoders-agency/skills/coolify-deploy/SKILL.md \
        local-plugins/nocoders-agency/.claude-plugin/plugin.json \
        local-plugins/nocoders-agency/.claude-plugin/marketplace.json
git commit -m "feat(nocoders-agency): add coolify-deploy skill, bump 2.6.0"
```

Note: if `~/.claude` is not a git repo or the plugin is tracked elsewhere, commit in the correct repo. The skill requires restart of Claude Code to appear in slash-commands — verification happens in Task 22.

---

## Task 17: Update `ag-mechanic` agent with Coolify-first policy

**Files:**
- Modify: `~/.claude/agents/ag-mechanic.md`

- [ ] **Step 17.1: Read the current agent file**

Run: `wc -l ~/.claude/agents/ag-mechanic.md`
Note the current line count and locate the three sections to modify: `## При старте (ОБЯЗАТЕЛЬНО)`, `## Рекомендуемые сервисы`, and find a good insertion point for the new `## Coolify deploy flow` section (after `## Что я делаю` is a good place).

- [ ] **Step 17.2: Add Coolify check to startup checklist**

In `## При старте (ОБЯЗАТЕЛЬНО)`, append this item (exact text):

```markdown
7. Если задача касается VPS или инфры — проверяю, установлен ли Coolify на целевом хосте (смотрю `docs/ops/coolify-preflight.md` в проекте или делаю SSH-проверку). Если Coolify есть — ОБЯЗАТЕЛЬНО читаю `~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md` ДО предложения любого деплой-действия И цитирую релевантный якорь секции (например, `playbook#p2--new-app-from-ghcr`) в своём ответе как доказательство чтения. Если Coolify нет — явно говорю: "Coolify не установлен. Рекомендую поставить его до деплоя — это наш стандарт для VPS продуктов. Деплой через docker-compose вручную = legacy путь."
```

- [ ] **Step 17.3: Reorder Recommended services**

Replace the `## Рекомендуемые сервисы` table. New default row at the top:

```markdown
| Категория | Сервис | Почему |
|-----------|--------|--------|
| **Деплой (default)** | Coolify (self-hosted) | Canonical для VPS, описан в playbook |
| **Деплой (alt)** | Railway | CLI + MCP — когда нет VPS |
| **Деплой (alt)** | Vercel | Preview deploys — serverless фронт |
| **Деплой (alt)** | Render | Managed — когда self-hosted непрактично |
...
```

Keep the rest of the table rows (DB, мониторинг, секреты, CI/CD) as they were.

- [ ] **Step 17.4: Add `## Coolify deploy flow` section**

Insert after `## Что я делаю` section:

```markdown
## Coolify deploy flow

Для любого деплоя на VPS, где стоит Coolify, canonical путь — `coolify-deploy` skill и playbook.

- Skill: `/coolify-deploy` (триггеры: "задеплой в coolify", "перенеси сервис в coolify").
- Playbook: `~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md`.
- При упоминании Coolify в задаче: читаю playbook, цитирую якорь секции, потом действую.
```

- [ ] **Step 17.5: Commit**

```bash
cd ~/.claude
git add agents/ag-mechanic.md
git commit -m "feat(ag-mechanic): Coolify-first policy with mandatory playbook read"
```

---

## Task 18: Create project scaffolds (GHCR registry access, prod cutover)

**Files:**
- Create: `~/Vibe/products/shkoderbot/docs/ops/ghcr-registry-access.md`
- Create: `~/Vibe/products/shkoderbot/docs/ops/vibe-gatekeeper-prod-cutover.md`

- [ ] **Step 18.1: Create GHCR registry access scaffold**

Write `docs/ops/ghcr-registry-access.md`:

```markdown
# GHCR Registry Access — vibe-gatekeeper

Document records the exact GHCR pull mechanism used for this project plus rotation history.

## Chosen mechanism

<filled by Spec B on <date>> — one of:
- host-level `docker login` (see playbook#p1 mechanism 1)
- Coolify Registry Credentials (see playbook#p1 mechanism 2)

## PAT details

- Token name: <filled by Spec B on <date>>
- Scope: `read:packages`
- Creation date: <filled by Spec B on <date>>
- Expiry date: <filled by Spec B on <date>>
- Calendar alerts set: 14 / 7 / 1 days before expiry — <filled by Spec B on <date>>

## Rotation log

| Date | Action | New token ID | Notes |
|------|--------|--------------|-------|
| <filled by Spec B on <date>> | initial | <filled by Spec B on <date>> | <filled by Spec B on <date>> |
```

- [ ] **Step 18.2: Create prod cutover scaffold**

Write `docs/ops/vibe-gatekeeper-prod-cutover.md`:

```markdown
# Vibe Gatekeeper Production Cutover Plan

Scaffold. Every `<filled by Spec C on <date>>` must be resolved before cutover.

## Data migration

- Postgres: `pg_dump` from legacy → `pg_restore` into Coolify Postgres. Command shape: <filled by Spec C on <date>>.
- Redis: approach chosen per playbook#p3 — <filled by Spec C on <date>> (drain / RDB copy / accept loss).
- Google credentials: mounted at `/app/credentials.json`, mode 0400. Transfer procedure: <filled by Spec C on <date>>.

## Cutover window

- Scheduled time: <filled by Spec C on <date>>.
- Expected duration (per playbook#p6 timing budget × 2): <filled by Spec C on <date>>.
- Announcement channel: <filled by Spec C on <date>>.

## Rollback commands (ready before cutover)

See playbook#p6 — copy the exact rollback runbook here with UUIDs and paths filled in:

```
<filled by Spec C on <date>>
```

## Legacy archive

- Archive path: `/root/vibe-gatekeeper-legacy-archive-<date>.tar.gz`.
- 72h silence window ends: <filled by Spec C on <date>>.
- Re-verification checkpoints (T+24h, T+48h): see playbook#p7 legacy-kept-warm contract.

## Secret rotation list

Executed BEFORE cleanup, per playbook#p7:

- [ ] bot token
- [ ] DB password
- [ ] Redis password
- [ ] Google service-account key
- [ ] GHCR PAT
- [ ] webhook secrets
- [ ] admin web password
- [ ] session secrets

## Shred procedure (filesystem-specific)

- Detected VPS filesystem: <filled by Spec C on <date>>.
- Chosen path (per playbook#p7): <filled by Spec C on <date>>.
- Commands: <filled by Spec C on <date>>.
```

- [ ] **Step 18.3: Commit**

```bash
cd ~/Vibe/products/shkoderbot
git add docs/ops/ghcr-registry-access.md docs/ops/vibe-gatekeeper-prod-cutover.md
git commit -m "docs(ops): scaffold ghcr-registry-access and prod-cutover for Spec B/C"
```

---

## Task 19: Update `runbook.md` with Coolify deploys section

**Files:**
- Modify: `~/Vibe/products/shkoderbot/docs/runbook.md`

- [ ] **Step 19.1: Check existing runbook sections**

Run: `grep -n '^## ' ~/Vibe/products/shkoderbot/docs/runbook.md`
Note whether `## Coolify deploys` and `## Known Issues & Quirks` already exist.

- [ ] **Step 19.2: Add `## Coolify deploys` section if missing**

Append to the runbook:

```markdown
## Coolify deploys

Canonical reference: `~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md` plus `/coolify-deploy` skill.

- **Start app:** Coolify UI → project → app → Start. CLI: `coolify start <app-uuid>` (if `coolify` CLI available on host) or `docker start <container-uuid>` as fallback.
- **Stop app:** Coolify UI → Stop, or `coolify stop <app-uuid>`.
- **Pull logs (last 500 lines, follow):** `coolify logs <app-uuid> --tail 500 --follow`; fallback `docker logs <container-uuid> --tail 500`.
- **Where secrets live:** Coolify env panel per app. On disk: `/data/coolify/...` (ACL 600 root:root). Never commit to git.
- **Rollback to previous digest:** Coolify UI → app → Deployments → select previous deployment → Redeploy. CLI path: update image reference in app config to the prior `@sha256:` digest, redeploy.

## Known Issues & Quirks

_Filled incrementally as Coolify migration reveals issues. Each entry format:_

```
### <YYYY-MM-DD> — <short issue>
Symptom:
Root cause:
Fix:
```
```

- [ ] **Step 19.3: Commit**

```bash
cd ~/Vibe/products/shkoderbot
git add docs/runbook.md
git commit -m "docs(runbook): add Coolify deploys and Known Issues sections"
```

---

## Task 20: Create handoff document for Specs B and C

**Files:**
- Create: `~/Vibe/products/shkoderbot/docs/superpowers/handoffs/2026-04-19-coolify-bc-handoff.md`

- [ ] **Step 20.1: Create handoff directory**

Run: `mkdir -p ~/Vibe/products/shkoderbot/docs/superpowers/handoffs`
Expected: command succeeds (existing dir is ok).

- [ ] **Step 20.2: Write handoff with the 6 mandatory sections**

Per spec `A8`, the file must contain these 6 sections in order:

```markdown
# Coolify B+C Handoff — vibe-gatekeeper

Self-contained prompt for the session executing Spec B (staging cutover) and Spec C (production cutover + legacy removal). A new session can execute B and C using only this file plus the playbook at `~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md` and the project docs in `~/Vibe/products/shkoderbot/docs/ops/`.

Once Spec B starts executing, this file is frozen. New decisions during execution go into the playbook Recommendations section or project docs, never edits here.

## 1. Frozen decisions from Spec A

- GHCR pull mechanism: defaults to host-level `docker login` per current reality (2026-04-19 runbook entry). Playbook `p1` documents both mechanisms; Spec B records final choice.
- Proxy strategy recommendation: migrate vaultwarden into Coolify (playbook `p0.1`). Alternatives documented; Spec B picks.
- Observability baseline: healthchecks.io + TG alert + Sentry + error-rate / disk-free / OOM / 5xx alerts.
- Data migration: staging clean, prod `pg_dump`/`pg_restore`, Google creds as mounted file 0400, Redis state per playbook `p3`.
- Legacy removal: immediately after 48h prod monitoring window, secret rotation before cleanup, FS-specific shred, 72h kept-warm contract.
- `ag-mechanic`: Coolify-first default with mandatory playbook read and anchor citation.

## 2. Open Items deferred to Spec B

- Exact vaultwarden resolution (migrate / remove / alt-port).
- Concrete Alembic migration hook style pinned inside Coolify.
- Measured cutover timing budget (filled into `p6`).
- Fallback registry decision.
- Staging-ACME / backup certificate procedure.
- Secondary external observer pick (UptimeRobot / Pingdom / 2nd healthchecks.io).
- Final GHCR pull mechanism recorded in Recommendations section.

## 3. Command shapes ready to use

```
pg_dump --host=<legacy-host> --username=<user> --format=custom --file=/tmp/vibe-prod-$(date +%F).dump <db>
pg_restore --host=<coolify-pg-uuid> --username=<user> --dbname=<db> --no-owner /tmp/vibe-prod-<date>.dump
redis-cli -h <legacy-redis-host> --rdb /tmp/vibe-redis-$(date +%F).rdb
scp /tmp/vibe-redis-*.rdb <coolify-redis-volume-path>
```

## 4. Rollback commands pinned to current legacy digest

```
# Current legacy paths:
#   compose:  /home/claw/vibe-gatekeeper/docker-compose.yml
#   env:      /home/claw/vibe-gatekeeper/.env
# During cutover, compose is renamed to docker-compose.yml.locked-during-cutover.
# Rollback:
cd /home/claw/vibe-gatekeeper
mv docker-compose.yml.locked-during-cutover docker-compose.yml
docker compose up -d
curl -s "https://api.telegram.org/bot$BOT_TOKEN/getUpdates" | jq '.ok'   # expect true, no 409
```

## 5. Smoke-check list including E2E

Follow playbook `p5`. Infra checks plus this specific E2E for vibe-gatekeeper:
- test account applies → another test account vouches → admin approves → invite received.

## 6. Canonical references

- Playbook: `~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md`. Current STATUS: UNVERIFIED DRAFT. Every section touched by Spec B must update its `verified_on`.
- Spec A: `~/Vibe/products/shkoderbot/docs/superpowers/specs/2026-04-19-coolify-knowledge-layer-design.md`.
- This handoff: frozen once Spec B begins.
```

- [ ] **Step 20.3: Commit**

```bash
cd ~/Vibe/products/shkoderbot
git add docs/superpowers/handoffs/2026-04-19-coolify-bc-handoff.md
git commit -m "docs(handoffs): create B+C cutover handoff (Spec A deliverable)"
```

---

## Task 21: Create `verified_on` enforcement wrapper script and test

**Files:**
- Create: `~/Vibe/scripts/check-verified-on.sh`
- Create: `~/Vibe/scripts/test-check-verified-on.sh`

- [ ] **Step 21.1: Ensure scripts dir exists**

Run: `mkdir -p ~/Vibe/scripts`
Expected: dir exists.

- [ ] **Step 21.2: Write the enforcement script**

Create `~/Vibe/scripts/check-verified-on.sh` with exactly:

```bash
#!/usr/bin/env bash
# check-verified-on.sh — enforce verified_on markers in the Coolify playbook.
# Fails when a `# p*` section in the playbook has `verified_on: never` or a date older
# than 30 days without an explicit `verified_on-exempt: <reason>` annotation.
#
# Usage: ./check-verified-on.sh [path-to-playbook]
# Default path: ~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md

set -euo pipefail

PLAYBOOK="${1:-$HOME/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md}"
if [[ ! -f "$PLAYBOOK" ]]; then
  echo "ERROR: playbook not found at $PLAYBOOK" >&2
  exit 2
fi

STALE_DAYS=30
NOW_EPOCH=$(date +%s)
STALE_CUTOFF=$(( NOW_EPOCH - STALE_DAYS * 86400 ))

# Parse sections: split on ^# lines, collect per-section verified_on value and optional exempt flag.
awk -v cutoff="$STALE_CUTOFF" '
  BEGIN { section=""; section_has_verified=0; verified_value=""; exempt=0; bad=0 }
  /^# p[0-9]/ {
    if (section != "" && section_has_verified) {
      process_section()
    }
    section=$0; section_has_verified=0; verified_value=""; exempt=0
    next
  }
  /^verified_on:/ {
    section_has_verified=1
    verified_value=$2
    next
  }
  /^verified_on-exempt:/ {
    exempt=1
    next
  }
  END {
    if (section != "" && section_has_verified) process_section()
    exit bad
  }
  function process_section() {
    if (exempt) return
    if (verified_value == "never") {
      printf "FAIL: %s has verified_on: never\n", section
      bad=1
      return
    }
    cmd = "date -j -f %Y-%m-%d " verified_value " +%s 2>/dev/null || date -d " verified_value " +%s 2>/dev/null"
    cmd | getline sec_epoch
    close(cmd)
    if (sec_epoch == "" || sec_epoch+0 < cutoff+0) {
      printf "FAIL: %s has stale verified_on: %s (cutoff %d days)\n", section, verified_value, 30
      bad=1
    }
  }
' "$PLAYBOOK"
```

Make it executable: `chmod +x ~/Vibe/scripts/check-verified-on.sh`.

- [ ] **Step 21.3: Write a failing-case test**

Create `~/Vibe/scripts/test-check-verified-on.sh`:

```bash
#!/usr/bin/env bash
# Failing-case test for check-verified-on.sh.
# Creates a throwaway playbook with verified_on: never and confirms the check FAILS.

set -euo pipefail

TMP=$(mktemp -d)
trap "rm -rf $TMP" EXIT

cat > "$TMP/bad-playbook.md" <<'EOF'
# Coolify Deploy Playbook

# p1 — test
verified_on: never

# p2 — test
verified_on: 2020-01-01
EOF

if "$(dirname "$0")/check-verified-on.sh" "$TMP/bad-playbook.md"; then
  echo "TEST FAILED: script should have exited non-zero on bad playbook" >&2
  exit 1
fi

echo "TEST PASSED: script correctly flagged stale and never markers"
```

Make executable: `chmod +x ~/Vibe/scripts/test-check-verified-on.sh`.

- [ ] **Step 21.4: Run the test to prove the check works**

Run: `~/Vibe/scripts/test-check-verified-on.sh`
Expected output: `TEST PASSED: script correctly flagged stale and never markers` and exit 0.

- [ ] **Step 21.5: Commit (where ~/Vibe/scripts lives in git)**

If `~/Vibe/` is git-tracked:
```bash
cd ~/Vibe
git add scripts/check-verified-on.sh scripts/test-check-verified-on.sh
git commit -m "tools: add verified_on enforcement check for coolify playbook"
```

If `~/Vibe/` is not git-tracked, note this in `Recommendations & Lessons Learned` as a followup item ("move scripts into a git-tracked location for durability"). Spec B may decide the long-term home.

---

## Task 22: Final verification against Spec A success criteria

**Files:** none (verification only).

- [ ] **Step 22.1: A1 — playbook exists with full structure**

Run: `grep -nE '^# (Overview|p[0-9]|Recommendations)' ~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md`
Expected: 16 lines matching (Overview, p0, p0.1, p1, p2, p3, p3.5, p4, p5, p6, p7, p8, p9, p10, p11, Recommendations).

Run: `grep -c '^verified_on: never' ~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md`
Expected: 14 (one per procedure section; Overview and Recommendations don't carry `verified_on`).

- [ ] **Step 22.2: A2 — skill registers**

Restart Claude Code, then in a new session check that `/coolify-deploy` appears in slash-command autocomplete.
Expected: `/coolify-deploy` is listed.

- [ ] **Step 22.3: A3 — ag-mechanic updated**

Run: `grep -n 'Coolify' ~/.claude/agents/ag-mechanic.md | head`
Expected: at least one line inside `## При старте` referencing the playbook path, at least one line in `## Рекомендуемые сервисы` with Coolify at default, and a `## Coolify deploy flow` section header.

- [ ] **Step 22.4: A4, A5 — project scaffolds and runbook**

Run: `ls ~/Vibe/products/shkoderbot/docs/ops/ghcr-registry-access.md ~/Vibe/products/shkoderbot/docs/ops/vibe-gatekeeper-prod-cutover.md`
Expected: both files present.

Run: `grep -nE '^## (Coolify deploys|Known Issues & Quirks)' ~/Vibe/products/shkoderbot/docs/runbook.md`
Expected: both section headers found.

- [ ] **Step 22.5: A6 — placeholder scan**

Run this exact command:

```bash
grep -rniE '\b(TBD|TODO|FIXME)\b' \
  ~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md \
  ~/.claude/local-plugins/nocoders-agency/skills/coolify-deploy/SKILL.md \
  ~/Vibe/products/shkoderbot/docs/superpowers/specs/2026-04-19-coolify-knowledge-layer-design.md \
  ~/Vibe/products/shkoderbot/docs/ops/ghcr-registry-access.md \
  ~/Vibe/products/shkoderbot/docs/ops/vibe-gatekeeper-prod-cutover.md \
  ~/Vibe/products/shkoderbot/docs/runbook.md
```

Expected: the only hits are inside quoted prohibition text in the spec or explicit `<filled by Spec B on <date>>` / `<filled by Spec C on <date>>` markers. No unguarded hits.

- [ ] **Step 22.6: A7 — enforcement test green**

Run: `~/Vibe/scripts/test-check-verified-on.sh`
Expected: `TEST PASSED`.

Run (positive case): `~/Vibe/scripts/check-verified-on.sh`
Expected: exit 1 with a list of `FAIL: # p... has verified_on: never` lines (this is correct behavior — the playbook is UNVERIFIED DRAFT; Spec B will flip markers).

- [ ] **Step 22.7: A8 — handoff self-contained**

Run: `grep -nE '^## ' ~/Vibe/products/shkoderbot/docs/superpowers/handoffs/2026-04-19-coolify-bc-handoff.md`
Expected: six section headers (1 Frozen decisions, 2 Open Items, 3 Command shapes, 4 Rollback, 5 Smoke-check, 6 Canonical references).

- [ ] **Step 22.8: Final commit (if anything was adjusted during verification)**

```bash
# Only if 22.1–22.7 revealed fixable deltas
cd ~/Vibe/products/shkoderbot
git add -A
git commit -m "docs(coolify-knowledge): post-verification fixes"
```

Otherwise, skip. End of plan.

---

## Self-Review Notes

- Spec coverage: each success criterion A1..A8 has at least one task or verification step (Task 1–15 → A1; Task 16 → A2; Task 17 → A3; Task 18 → A4; Task 19 → A5; Task 22.5 → A6; Task 21 → A7; Task 20 → A8).
- Placeholder discipline: plan contains `<filled by Spec B on <date>>` / `<filled by Spec C on <date>>` inside file templates only; no naked TBD/TODO in instructions.
- Type consistency: anchor slugs match between skill (`playbook#p35--persistent-volumes--backup`) and playbook canonical anchor list. Plugin name `nocoders-agency` and marketplace `nocoders-agency-marketplace` are consistent across Tasks 16 and Pre-Flight 0.2.
- TDD note: this plan is docs-heavy. TDD manifests as "write structure → verify grep → commit" loops and as the explicit failing-case test for the enforcement script in Task 21.
