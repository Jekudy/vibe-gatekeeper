# Coolify Knowledge Layer Design (Spec A)

Date: 2026-04-19
Status: Draft for review
Related prior spec: `~/Vibe/products/shkoderbot/docs/superpowers/specs/2026-04-12-vps-git-ghcr-coolify-design.md`

## Sub-Project Legend

This spec is the knowledge layer. It is part of a four-part decomposition:

- **Spec A (this doc)** — knowledge layer: playbook, skill, agent update, project doc scaffolds.
- **Spec B** — staging cutover for `vibe-gatekeeper` (separate session).
- **Spec C** — production cutover + legacy removal (separate session).
- **Spec D** — Shkoder feature expansion (discovery + implementation, later).

## Goal

Establish a durable knowledge layer that encodes how Coolify deploys work in this environment so that:

- Any future Coolify migration (starting with `vibe-gatekeeper` staging and prod) follows one canonical procedure.
- `ag-mechanic` defaults to Coolify when a VPS is involved and flags its absence when it is missing.
- The same body of knowledge is reusable across products on the same VPS (confirmed second use-case: `foodzy`).

The knowledge layer is written first and updated iteratively by Specs B and C as they execute the actual cutover.

## Scope

### In scope (this spec)

- Canonical deploy playbook at `~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md`.
- Operational skill at `~/.claude/local-plugins/nocoders-agency/skills/coolify-deploy/SKILL.md` plus namespace reservation for `coolify-*`.
- `~/.claude/agents/ag-mechanic.md` update with a Coolify-first default policy and explicit playbook-read trigger.
- Project-specific doc scaffolds in `~/Vibe/products/shkoderbot/docs/ops/`.
- Self-contained handoff prompt at `~/Vibe/products/shkoderbot/docs/superpowers/handoffs/2026-04-19-coolify-bc-handoff.md` for Specs B and C.

### Out of scope

- Execution of Spec B (staging cutover) and Spec C (production cutover + legacy removal).
- Spec D (Shkoder feature expansion).
- Migration of non-product services (`vaultwarden`, `radicale`, `fast-mcp-telegram`) into Coolify, except where proxy-strategy and its dedicated sub-procedure (vaultwarden cutover) are documented as generic patterns.
- High-availability or multi-node Coolify topology.
- Multi-VPS topology (the playbook assumes single-host until a multi-host use-case appears).

## Context (already established)

- Source of truth for `vibe-gatekeeper` is `github.com/Jekudy/vibe-gatekeeper`.
- CI is green. Release workflow publishes immutable images to GHCR (`ghcr.io/jekudy/vibe-gatekeeper-bot`, `-web`).
- Coolify is installed on the VPS, dashboard bound to Tailscale IP only at `http://100.101.196.21:8100`. Root admin bootstrap completed on 2026-04-12. Localhost SSH fix applied.
- Legacy runtime stays live at `/home/claw/vibe-gatekeeper` until the new path is verified.
- Pull blocker: GHCR images are private, Coolify does not hold a `read:packages` credential yet.
- Telegram bot uses polling, so two runtimes cannot share one token. Simultaneous use produces `error_code: 409 Conflict`.
- Same VPS hosts `vaultwarden-caddy` on `80/443`, `radicale`, `fast-mcp-telegram`, `foodzy-bot`, `foodzy-postgres`, and `claude-tg-watchdog` (systemd).
- Detailed VPS facts already exist at `~/Vibe/products/shkoderbot/docs/ops/coolify-preflight.md` and `~/Vibe/products/shkoderbot/docs/ops/vibe-gatekeeper-staging-cutover.md`. Both files are inputs to this spec, not outputs.

## Artefact Architecture

Three artefacts with distinct responsibilities. Each has a defined scope and must not duplicate the others.

```
~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md
    Canonical, reusable, generic. Anchors define Overview + p0..p11.
    STATUS marker + per-section verified_on field + pinned Coolify
    version. Concept, architecture, decisions, full procedures.

~/.claude/local-plugins/nocoders-agency/skills/coolify-deploy/SKILL.md
    Operational. Triggers in Russian (voice-input tolerant).
    References playbook sections by anchor. Contains call order,
    prerequisite list, and parameter slot templates ONLY. Never
    restates procedure steps.

~/.claude/agents/ag-mechanic.md
    Behavioral update. Coolify-first default. Explicit playbook-read
    trigger on Coolify topics. Recommended-services order changed.
    Cites playbook anchors in its output as evidence of having read.

~/Vibe/products/shkoderbot/docs/ops/
    Project-specific facts. Scaffolded by this spec, filled by
    Specs B and C. No reusable knowledge lives here.
```

### Boundary rule

- Playbook owns the knowledge (what to do, why, alternatives).
- Skill owns the triggers, the call order, and parameter slot templates.
- Agent owns the default behavior and the mandatory playbook read.
- Project docs own the filled-in parameter values (image names, hostnames, secrets paths, env values).

If a topic appears in two artefacts it must be relocated to the owning artefact and referenced from the other.

### Anchor format

All playbook headings use GitHub-style slug rules:

- `# Overview` → `#overview`
- `# p0 — Prereq & network topology` → `#p0--prereq--network-topology`
- `# p3.5 — Persistent volumes & backup` → `#p35--persistent-volumes--backup`

The skill and agent must use these exact slugs when cross-referencing. The playbook header lists all canonical anchors explicitly so drift is detectable.

## ag-mechanic Coolify-First Policy

This is a behavioral change, not a cosmetic doc change.

### Changes to `~/.claude/agents/ag-mechanic.md`

1. In `## При старте (ОБЯЗАТЕЛЬНО)`, add a required check: when the context mentions a VPS, deploy, or infrastructure work, the agent must verify whether Coolify is installed on the target host (presence of `docs/ops/coolify-preflight.md` in the project, or direct SSH check). If Coolify is present, the agent must read the canonical playbook before proposing any deploy action **and cite the relevant playbook anchor (e.g., `playbook#p2--new-app-from-ghcr`) in its response as evidence of having read**. If Coolify is absent, the agent must flag this explicitly:

   > Coolify не установлен. Рекомендую поставить его до деплоя — это наш стандарт для VPS продуктов. Деплой через docker-compose вручную = legacy путь.

2. In `## Рекомендуемые сервисы`, move Coolify (self-hosted) to the top of the deploy category:
   - **Деплой (default)**: Coolify (self-hosted).
   - **Деплой (alternative)**: Railway, Vercel, Render — only when Coolify is impractical (serverless, managed platform-only, vendor-specific).

3. Add a new section `## Coolify deploy flow` with a short paragraph and links to the canonical playbook and `/coolify-deploy` skill.

### Discoverability

- The playbook-read trigger is explicit ("Read the playbook before answering + cite an anchor"), not implicit.
- Related skills reserve the `coolify-*` namespace so future skills (`coolify-debug`, `coolify-rollback`) plug in without collision.

## Playbook Content Specification

Location: `~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md`.

### Required header

```markdown
# Coolify Deploy Playbook

STATUS: UNVERIFIED DRAFT
Coolify version tested: <exact version | none>
Last validated against: <project, date | never>
Canonical anchors: overview, p0, p0.1, p1, p2, p3, p3.5, p4, p5, p6, p7, p8, p9, p10, p11, recommendations
```

`Coolify version tested` is mandatory — the executor must fill it with the actual version running on the host at write time (e.g., `v4.0.0-beta.x`). Sessions that upgrade Coolify update this field in the same PR.

Each procedure section (`p0`..`p11`) carries its own line:

```
verified_on: <YYYY-MM-DD | never>
```

### Enforcement of `verified_on`

PRs that change any procedure section must update its `verified_on`. A repository-level pre-commit or CI check fails the PR if a changed section keeps `verified_on: never` or an outdated date. Writing the CI check itself is part of Spec A deliverables (see Success Criteria A7).

### Required sections

- `# Overview` — concept, Git → GHCR → Coolify flow, what Coolify owns vs what stays host-managed, Coolify-first default rationale, **Coolify exit strategy**: which primitives stay portable to Dokploy/Kamal/plain-compose (GHCR images, Dockerfile, env contracts, backup formats) vs which are Coolify-specific (webhook receiver, Traefik labels, Coolify secrets DB).
- `# p0 — Prereq & network topology` — VPS inventory, port usage, Tailscale posture, proxy strategy decision tree with all three paths written as full procedures, and recommendation (default: migrate vaultwarden into Coolify). Three paths to document fully:
  1. Migrate vaultwarden into Coolify — dedicated sub-procedure `p0.1` (see below).
  2. Remove vaultwarden — data export via `bw export` or server admin panel, decommission steps, DNS cleanup.
  3. Coolify Traefik on alt-port (8080/8443), front caddy proxies to it — example caddy block and Coolify `Traefik` label overrides, tech-debt note (two proxies to monitor).
  Also: `claude-tg-watchdog` systemd interaction with Coolify-managed bot (risk of double supervision, mitigation: watchdog only monitors host-level services, never Coolify-managed apps). Coolify webhook receiver security posture: Tailscale-only binding by default; if public webhook is required, protect with shared secret + IP allowlist.
- `# p0.1 — Vaultwarden cutover sub-procedure` — concrete steps with command shapes:
  1. Announce maintenance window; lock new registrations.
  2. `vaultwarden` dump: copy `/data/db.sqlite3` + `/data/attachments/` + `/data/config.json` to a staging dir, verify checksums.
  3. Stop legacy vaultwarden + caddy; free ports `80/443`.
  4. Deploy vaultwarden as a Coolify app (image `vaultwarden/server:latest` pinned by digest) with Traefik labels exposing the admin FQDN, TLS via Coolify-managed Let's Encrypt.
  5. Restore dump into Coolify-managed volume at the path the image expects (`/data`).
  6. Smoke: web login, known password retrieval on a secondary client, WebSocket sync.
  7. Rollback: stop Coolify vaultwarden app, restore caddy + legacy container, re-bind `80/443`, revert DNS if changed.
- `# p1 — GHCR pull` — two equally valid mechanisms, with selection guidance:
  1. **Host-level `docker login`** (recommended for single-tenant single-owner VPS). `docker login ghcr.io -u <owner>` as root on the VPS; credentials land in `/root/.docker/config.json`; Coolify reuses the host Docker daemon so no Coolify-side registry resource is needed. Pros: simplest to set up, one auth for all apps on the host. Cons: credentials shared across apps, rotation touches all apps simultaneously.
  2. **Coolify Registry Credentials** (recommended for multi-tenant or multi-registry setups). Fine-grained Owner PAT with `read:packages` added to Coolify Registry Credentials; blue/green rotation (two active PATs during overlap). Pros: per-credential isolation, Coolify-native rotation UI, supports multiple registries cleanly. Cons: extra Coolify resource, more click-ops.
  Common to both: PAT with `read:packages` scope only, 90-day expiry, expiry calendar alerts (14/7/1 days), `@sha256:` digest pinning instead of mutable tags. Fallback registry note: local self-hosted registry on the same VPS as disaster cache if GHCR is unreachable (optional, flagged as future work).
- `# p2 — New app from GHCR` — app creation, image reference (digest-pinned), env/volumes/resource limits, `depends_on`-equivalent in Coolify (Coolify groups apps and services but does not guarantee DB readiness at container start), **Alembic migration execution model** (init-container vs entrypoint vs Coolify pre-deploy command — choose and pin one; Spec B pins the choice), wait-for-it entrypoint retry loop, **advisory lock for concurrent migration runs** (mandatory note even for current single-replica bot, so multi-replica deploys later do not race on migration), **migration rollback policy** (forward-fix default; downgrade only when explicitly required and tested; pre-migration DB snapshot mandatory), Coolify webhook endpoint security (shared secret + IP allowlist if public).
- `# p3 — Database services` — managed Postgres and Redis in Coolify, DSN wiring, **Redis state transfer options** (drain-pending-flows / RDB copy / accept loss with announcement), restore drill procedure.
- `# p3.5 — Persistent volumes & backup` — explicit mount paths, backup cron, restore drill, **encrypt Coolify backups with age or sops**, key storage outside the backup destination, **Google credentials as mounted file with mode 0400, not env**, exclusion of secret volumes from Coolify backup scope where appropriate.
- `# p4 — Healthcheck & polling-conflict detection` — deep healthcheck endpoint spec (polling alive + DB ping + Redis ping), HTTP 200 on `/health`, Coolify healthcheck interval pinned (default: every 30 seconds) and consecutive-fail threshold (3 failures = unhealthy, so rollback trigger window = 90 seconds), external uptime via healthchecks.io cron ping from inside the bot every 5 minutes, TG alert wiring, **active detection of Telegram 409 Conflict** (bot logs it, Coolify pipes it to TG alert with a separate template), pre-cutover `getUpdates` probe.
- `# p5 — Smoke checks` — infra list (bot starts, web login, migrations apply, Redis works, scheduler starts, Google creds mounted) plus a scripted product-specific happy-path E2E (for `vibe-gatekeeper`: apply → vouch → approve) plus a log-access procedure (`coolify logs --tail 500 --follow` or docker fallback) that is grabbed **before** any rollback. Log retention verification pre-cutover (Coolify default retention may be shorter than legacy journald).
- `# p6 — Cutover & rollback as executable runbook` — measured stop→start budget from staging, hard 60s startup timeout, explicit SLI-based rollback triggers (polling lag > 30s, error rate > 5%, healthcheck fails 3x in a row), and a numbered rollback runbook (not just triggers):
  1. Verify legacy runtime fully stopped before starting new app.
  2. Start new app.
  3. If triggers fire within 5 minutes: capture logs from new app, stop new app via Coolify, revert token ownership if rotated, start legacy compose at pinned digest or tag, verify polling resumes, post-mortem log snapshot.
  Also: lock mechanism preventing accidental `docker compose up` on legacy during cutover window (e.g., temporary rename of legacy compose file); pre-cutover `getUpdates` probe proving no other runtime holds the token.
- `# p7 — Legacy cleanup` — rotate **all** secrets before cleanup. Explicit rotation list (not generic): bot token, DB password, Redis password if any, Google service-account key, GHCR PAT, webhook secrets, admin web password, session secrets. Then: `shred -u` on `.env` files — note that `shred` cannot guarantee erasure on journaling filesystems (ext4/btrfs/zfs are the realistic options here); Spec B records the actual VPS filesystem and picks one of: (a) overwrite-then-unlink plus `fstrim -v /`, (b) rely on full-disk encryption if present, (c) wipe the owning volume. Then: `swapoff -a && swapon -a`, journald log purge for entries containing tokens, archive retention window (72h), **legacy-kept-warm contract**: during the 72h window, legacy compose must be start-able within 5 minutes; periodic verification (T+24h, T+48h) is required.
- `# p8 — Disk & IOPS precheck for dual-stack window` — `df -h` snapshot + 7-day disk-growth trend check, `iostat`, thresholds (free < 20 GB or IO wait > 20% blocks the cutover).
- `# p9 — Observability baseline` — healthchecks.io cron ping from the bot every 5 minutes, TG alert in admin chat. Also required: error-rate alert (structured log grep or Sentry), disk-free alert (< 10 GB), OOM-kill alert, Traefik 5xx rate alert. Sentry is the recommended structured-error path for production and should be treated as the default rather than optional.
- `# p10 — Secrets & access hygiene` — Coolify secret storage on disk (ACL 600 root:root, path, plaintext-on-FS risk), RBAC in Coolify, Tailscale break-glass path if Tailnet or Tailscale control plane is down (documented as first-class flow, not emergency-only: direct SSH with specific host key, firewall rule, recovery runbook).
- `# p11 — Troubleshooting table` — 5–7 concrete failures with exact commands: `denied` / `unauthorized` on GHCR pull, port conflict on boot, DB DSN mismatch, volume permission denied, Coolify Traefik not binding 80/443 because another service holds it, admin UI unreachable due to Tailnet issue, healthcheck flapping, **Coolify self-failure mode** (if Coolify agent or proxy crashes, product containers continue via Docker but deploy/logs unavailable — `docker ps | grep <app>` fallback, no external watchdog for Coolify itself).
- `# Recommendations & Lessons Learned` — accumulative living section appended after `p11`. Each migration or significant Coolify work (Spec B, Spec C, foodzy migration, any future product migration) must add 1–3 entries in the form:
  ```
  ## <YYYY-MM-DD> — <short title>
  Context: <what we were doing>
  Lesson: <what we learned / what worked / what did not>
  Playbook impact: <which sections updated, or "no change">
  ```
  This section is the single collection point for operational recommendations. The skill and ag-mechanic reference it explicitly so experience compounds. Entries are immutable once committed (append-only); corrections go as new entries with back-reference.

### Prohibited content

- Project-specific values (image names, env keys, secrets, hostnames) — those live in project docs.
- Silent TBD, TODO, or unmarked placeholders. Explicit `<filled by Spec B on <date>>` markers are allowed and required for anything the first draft cannot verify.

## Skill Specification

Location: `~/.claude/local-plugins/nocoders-agency/skills/coolify-deploy/SKILL.md`.

### Frontmatter

- `name`: `coolify-deploy`
- `description`: Russian triggers — "задеплой в coolify", "перенеси сервис в coolify", "настрой ghcr pull в coolify", "подключи кулифай к репе". Must be specific enough not to fire on generic "deploy" talk.
- `version`: `1.0.0` on first creation (mirror in `plugin.json` and `marketplace.json`). Any material change bumps this everywhere.

### Body (strict structure)

- `## When to use / when NOT` — 4–5 lines.
- `## Prerequisites` — VPS with Coolify installed, `gh` CLI authenticated, Dockerfile in repo, GHCR images built by CI, playbook readable at its canonical path.
- `## Call order` — anchor references only, no procedural verbs:
  1. `playbook#p1--ghcr-pull`
  2. `playbook#p2--new-app-from-ghcr`
  3. `playbook#p3--database-services`
  4. `playbook#p35--persistent-volumes--backup`
  5. `playbook#p4--healthcheck--polling-conflict-detection`
  6. `playbook#p5--smoke-checks`
  7. `playbook#p6--cutover--rollback-as-executable-runbook` (only when migrating an existing service)
  Optional follow-up: `playbook#p7--legacy-cleanup`.
- `## Parameter slot template` — named slots the caller fills in project docs: `IMAGE_NAME`, `IMAGE_DIGEST`, `DOMAIN`, `ENV_KEYS`, `DB_DSN_SHAPE`, `BOT_TOKEN_VAR`, `GOOGLE_CREDS_MOUNT_PATH`. Slot values themselves live in project docs, never in the skill.
- `## Troubleshooting` — single-line pointer: `See playbook#p11--troubleshooting-table`. No local table.
- `## Recommendations` — single-line pointer: `See playbook#recommendations--lessons-learned`. No local content; the living section lives in the playbook.
- `## Link` — canonical playbook path.

### Release

- After creation or any change: bump version in `plugin.json` and `marketplace.json`, run `claude plugin update "nocoders-agency@<marketplace-name-from-plugin.json>"`, restart Claude Code.

## Project-Specific Scaffolds (shkoderbot)

These files are created empty-but-structured by this spec. Specs B and C fill them in with live data.

- `~/Vibe/products/shkoderbot/docs/ops/ghcr-registry-access.md` — PAT name, scope (`read:packages`), creation date, expiry, blue/green rotation log, Coolify Registry Credentials entry name. Existing file `docs/ops/coolify-preflight.md` and `docs/ops/vibe-gatekeeper-staging-cutover.md` are inputs, not created here.
- `~/Vibe/products/shkoderbot/docs/ops/vibe-gatekeeper-prod-cutover.md` — prod cutover plan scaffold: data migration (pg_dump/pg_restore, Redis transfer decision), cutover window, rollback commands, legacy archive path, 72h silence window, secret rotation list, shred procedure.
- `~/Vibe/products/shkoderbot/docs/runbook.md` — add a `## Coolify deploys` section (start/stop commands via Coolify CLI or UI, how to pull logs, where secrets live, how to rollback to a previous digest) and maintain `## Known Issues & Quirks` as the cutover reveals them.

## Handoff Document (Specs B and C)

Location: `~/Vibe/products/shkoderbot/docs/superpowers/handoffs/2026-04-19-coolify-bc-handoff.md`.

This file is a Spec A deliverable. It is the self-contained prompt for the session that executes Specs B and C, and it includes:

- Confirmed GHCR strategy (private + PAT, blue/green rotation).
- Confirmed data migration approach (staging clean, prod dump/restore, Google creds as file).
- Confirmed legacy cutoff and mitigation (72h archive window, secret rotation first).
- Smoke-check list including product-specific happy-path E2E.
- Reference to the canonical playbook with the expectation that `verified_on` markers are updated during execution.

## Decisions (single source of truth)

These decisions are final for this design. Playbook sections reference them; Risks and Open Items do not restate them.

- **GHCR identity**: Owner PAT with `read:packages`, 90-day expiry. Tenancy model can expand over time, so the playbook documents two equally valid pull mechanisms (host-level `docker login` and Coolify Registry Credentials) with "when to use which" guidance. Current shkoderbot cutover uses host-level `docker login`. Machine account deferred until a second human collaborator appears.
- **Audit depth**: post-mortem log analysis is the baseline; per-app structured audit trail for registry pulls is deferred until a compliance requirement or a team-growth event triggers it.
- **Proxy strategy recommendation**: migrate `vaultwarden` into Coolify so Coolify Traefik cleanly owns `80/443`. Alternatives (remove / alt-port) documented in `p0`; Spec B records the final choice.
- **Foodzy**: confirmed second use-case; the generic playbook is justified. Multi-VPS is out of scope until a multi-host use-case appears.
- **Observability baseline**: healthchecks.io cron ping + TG alert in admin chat. Sentry treated as recommended default for production error paths, not optional.
- **Data migration**: staging starts clean, prod uses `pg_dump` / `pg_restore` plus a Redis state decision per `p3`, Google creds mounted as file with mode 0400.
- **Legacy removal**: immediately after a 48h prod monitoring window passes, with full mitigation (secret rotation before cleanup, shred + caveats, swap wipe, journald purge, archived compose kept runnable for 72h with periodic re-verification).
- **ag-mechanic behavior**: Coolify-first by default, mandatory playbook read with anchor citation, flags missing Coolify.

## Dependency Gates

- **Downstream gate**: no downstream project (foodzy Coolify adoption, Spec D, any second-product migration) starts until the canonical playbook's STATUS transitions from `UNVERIFIED DRAFT` to `VALIDATED` as a result of Spec B or Spec C execution. Enforcement: the `verified_on` CI check (see A7) plus a one-line gate requirement in the downstream spec's Scope section.
- **Handoff freeze**: once Spec B starts execution, `2026-04-19-coolify-bc-handoff.md` is frozen. Any new decisions that arise during execution are recorded inside the playbook (`verified_on` update) or in project docs, not by editing the handoff file.
- **Skill version bump ownership**: any change to procedure call order, slot template, or troubleshooting pointer triggers a version bump by the session making the change; the bump is part of the same PR. No silent edits.

## Risks

Enumerated without repeating mitigations already encoded in Decisions or Playbook sections.

- **Playbook rot**: generic knowledge stales silently. Mitigation: `verified_on` markers + CI enforcement gate (Success Criterion A7).
- **Coolify upstream drift**: UI labels and defaults change between Coolify versions. Mitigation: pinned `Coolify version tested` header; upgrade treated as a gated change requiring playbook re-validation.
- **Coolify exit cost**: vendor lock-in if we go all-in. Mitigation: Overview section documents portable primitives and exit path.
- **Single points of failure**: Owner PAT (bus-factor 1), Tailscale control plane (admin UI reachability), healthchecks.io (single external observer), iCloud sync for playbook storage (possible stale reads during outage). Mitigations: rotation calendar, SSH break-glass as first-class flow, optional secondary observer, and a rule to read the playbook from the git-tracked canonical commit when iCloud is suspected to be stale.
- **DNS/ACME**: Let's Encrypt rate-limits or DNS failure blocks public HTTPS. Mitigation: staging ACME path and backup cert procedure documented in `p0`/`p2` (follow-up; tracked as Open Item).
- **Agent behavior enforcement**: `ag-mechanic` read-playbook rule is normative. Mitigation: anchor-citation requirement makes compliance grep-auditable from session transcripts.

## Open Items (decisions deferred to Spec B)

- Exact `vaultwarden` resolution executed (migrate vs remove vs alt-port) — playbook `p0` documents all three fully; Spec B records the chosen path.
- Concrete Alembic migration hook style pinned inside Coolify — `p2` documents options; Spec B pins one.
- Measured cutover timing budget — filled into `p6` by Spec B after staging rehearsal.
- Fallback registry decision (self-hosted on same VPS) — tracked but not required for initial cutover.
- Staging-ACME / backup certificate procedure detailed — tracked in `p0`/`p2` draft text, validated by Spec B.
- Secondary external observer for healthchecks.io — pick one (UptimeRobot, Pingdom, or a second healthchecks.io project on a different provider) so the observability baseline is not a single-vendor SPOF; decision and wiring deferred to Spec B.
- GHCR pull mechanism choice for shkoderbot cutover: reality (2026-04-19) chose host-level `docker login`. Spec B records the final choice in the playbook `Recommendations & Lessons Learned` section with reasoning, and updates `p1` `verified_on` accordingly.

## Success Criteria (Spec A)

- `A1`: `~/Vibe/knowledge/nocoders/docs/architecture/coolify-deploy-playbook.md` exists with the required header (STATUS, Coolify version, last validated, canonical anchors), `verified_on: never` on every procedure section, and all required sections populated with draft content (Overview, `p0`..`p11` including `p0.1` vaultwarden sub-procedure and `p3.5`, plus `Recommendations & Lessons Learned` as an empty-but-structured accumulating section).
- `A2`: `~/.claude/local-plugins/nocoders-agency/skills/coolify-deploy/SKILL.md` exists, references the playbook by anchor only (no procedural verbs in the call-order list), and passes `claude plugin update`; `/coolify-deploy` appears in slash-commands after restart.
- `A3`: `~/.claude/agents/ag-mechanic.md` contains the Coolify-first behavioral rule, the explicit playbook-read instruction, and the anchor-citation requirement. Coolify is top-of-list in Recommended services.
- `A4`: `~/Vibe/products/shkoderbot/docs/ops/ghcr-registry-access.md` and `~/Vibe/products/shkoderbot/docs/ops/vibe-gatekeeper-prod-cutover.md` scaffolds exist with explicit `<filled by Spec B on <date>>` placeholders and no silent TBDs. (`docs/ops/coolify-preflight.md` and `docs/ops/vibe-gatekeeper-staging-cutover.md` remain as pre-existing inputs and are not touched by A4.)
- `A5`: `~/Vibe/products/shkoderbot/docs/runbook.md` has a `Coolify deploys` section and a `Known Issues & Quirks` section.
- `A6`: Automated placeholder scan: `grep -rniE "\b(TBD|TODO|FIXME)\b" <playbook> <skill> <spec> <project-scaffolds>` returns only occurrences inside quoted prohibition text or explicit `<filled by Spec B>` markers — no unguarded hits. Scaffolds covered: `~/Vibe/products/shkoderbot/docs/ops/ghcr-registry-access.md`, `~/Vibe/products/shkoderbot/docs/ops/vibe-gatekeeper-prod-cutover.md`, `~/Vibe/products/shkoderbot/docs/runbook.md`.
- `A7`: A `verified_on` enforcement mechanism is documented and wired. Because the playbook lives in the iCloud-synced `~/Vibe/` vault, which is not a git repository with CI by default, this spec defines two acceptable mechanisms and pins one:
  1. Primary (chosen): a pre-commit hook at the Vibe vault level (`~/Vibe/.git/hooks/pre-commit` if the vault is git-tracked, otherwise a wrapper script `~/Vibe/scripts/check-verified-on.sh` invoked by any agent before committing changes that touch the playbook) that fails when a changed `# p*` section keeps `verified_on: never` or a date older than 30 days without an explicit `verified_on-exempt: <reason>` annotation.
  2. Fallback: the playbook is mirrored as a read-only copy into each consuming project repo (e.g., `shkoderbot/docs/coolify-playbook.md`) via a sync script, and a repo-level pre-commit enforces the same rule on the mirror.
  A7 passes when the chosen mechanism exists, has a concrete script or hook file, and a reproducible failing-case test (sample PR with `verified_on: never` fails the check).
- `A8`: `~/Vibe/products/shkoderbot/docs/superpowers/handoffs/2026-04-19-coolify-bc-handoff.md` exists and is self-contained. Self-containment is verified against a fixed checklist that the handoff must cover: (1) decisions frozen in Spec A (GHCR PAT, proxy recommendation, observability baseline, data migration, legacy removal), (2) full list of Open Items deferred to Spec B, (3) command shapes for `pg_dump`/`pg_restore` and Redis RDB copy, (4) rollback commands pinned to the current legacy digest or tag, (5) smoke-check list including the product-specific happy-path E2E, (6) explicit reference to the canonical playbook path and its current STATUS. A new session can execute Specs B and C using only the handoff file, the playbook, and project docs.
