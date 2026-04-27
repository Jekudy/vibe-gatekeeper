# Hard Code Review — Security Audit Cycle (2026-04-27)

**Trigger:** user-requested deep critique after 14-PR security audit cycle.
**Reviewers:** ag-partner (architectural), codex (technical, 2 passes), ag-sa (systems, 2 passes).
**Total findings:** 40 (10×4 = 30 in pass 1 + 5×2 in pass 2; deduplicated below).
**Status:** triage. P0 prod bugs to be fixed in next cycle, P1 to be tracked, P2 noted.

---

## P0 — Production-exploitable bugs (fix immediately)

### CRIT-01: Bearer invite + broad active-app admission = bypass vouching
**Class:** business-logic / auth
**Source:** codex pass-2 #1
**Files:** `bot/services/invite.py:13-17`, `bot/db/repos/application.py:30-35`, `bot/handlers/chat_events.py:90-143`
**Attack chain:**
1. Vouched user A receives invite (member_limit=1, name=`app-{app_id}`, NOT user-bound).
2. A forwards the invite to user B (no relationship to bot).
3. B sends `/start` → creates `filling` application.
4. B uses the invite link.
5. `_handle_join` accepts `filling`, `pending`, `privacy_block`, `vouched` as admissible (`get_active`).
6. B is marked `is_member=True`, app set `added`.
7. **B enters community without a voucher, without going through review.**
**Fix:** bind invite to specific user_id at creation time; admission filter in `chat_events` accepts ONLY `vouched` status; reject other states.

### CRIT-02: Telegram side effects before DB commit → ghost invites after rollback
**Class:** transaction-correctness / side-effect leak
**Source:** codex pass-2 #2
**Files:** `bot/handlers/vouch.py:61-73, 111-129`, `bot/middlewares/db_session.py:21-25`
**Failure path:**
1. Voucher clicks vouch → handler updates app status to `vouched` (uncommitted).
2. Handler sends Telegram invite (live external side effect).
3. `callback.answer()` or final commit fails for any reason.
4. DB rolls back to `pending`.
5. **Invite remains live in Telegram** — applicant joins via it.
6. `_handle_join` sees `pending`, accepts → membership created without durable vouch state, no `vouch_log` row, no audit trail.
**Fix:** outbox pattern — write outbox row in same transaction, commit, then send Telegram side effect from worker. OR `commit()` BEFORE invite send; on send failure re-queue (idempotent).

### CRIT-03: Auto-reject scheduler overwrites successful vouch (race + missing WHERE)
**Class:** race condition / unguarded UPDATE
**Source:** codex pass-2 #3
**Files:** `bot/services/scheduler.py:41-50`, `bot/db/repos/application.py:57-64`, `bot/handlers/vouch.py:61-73`
**Tests miss this:** `tests/test_scheduler_deadlines.py:25-35` — single SQLite flow, no concurrent interleaving.
**Failure path:**
1. Scheduler `check_vouch_deadlines` SELECT'ит pending apps.
2. While loop iterates, voucher концurrently updates app to `vouched`.
3. Scheduler reaches that app, calls `update_status(id, "rejected")` без `WHERE status='pending'` guard.
4. **Vouched user автоматически отклоняется**, но invite уже отправлен — фантомный member.
**Fix:** в `update_status` для auto-reject path использовать compare-and-set: `UPDATE applications SET status='rejected' WHERE id=:id AND status='pending'`. Проверять rowcount.

### CRIT-04: Empty WEB_SESSION_SECRET accepted by validator (cookie-forgery)
**Class:** cryptography misuse
**Source:** codex pass-1 #3
**Files:** `bot/config.py:42-49`, `web/auth.py:9-10`
**Bug:** validator проверяет `is None` но пропускает `""`. Cookie signing key = пустая строка → trivially forgeable signature.
**Fix:** validator требует `len(secret) >= 32`; fail fast если короче в любом DEV_MODE.

### CRIT-05: Coolify API token id=4 + WEB_SESSION_SECRET остаются скомпрометированы
**Class:** operational / leaked secret
**Source:** ag-partner #10 + ag-sa #1
**Action:** revoke Coolify token id=4 → создать новый → regen `WEB_SESSION_SECRET` (32-byte token_urlsafe) → update Coolify env → redeploy.
**Notes:** plaintext значения убраны из `memory/worklog.md` и `.handoffs/handoff_2026-04-26_20-05_n5-sha-pin.md` 2026-04-27, но **rotation pending до выполнения шагов выше**. До тех пор — assume both leaked.

### CRIT-06: Single-laptop kill chain (operator security)
**Class:** systems / single point of compromise
**Source:** ag-sa pass-2 #4 + partner #1
**Failure path:** founder's Mac compromise → одна точка отказа: SSH key + Tailscale identity + `~/.env.tokens` + 1Password Personal + git push на main + GHCR PAT. Tailscale-only без MFA усугубляет.
**Fix:**
- Отдельный YubiKey/passkey для git push на main (signed commits enforcement).
- Отдельная Tailscale identity для VPS access (не та же что dev daily).
- 1Password Personal — отделить admin secrets в свой vault с YubiKey.
- Backup recovery codes в bank safe deposit box (out-of-band).

---

## P0 — Missing prerequisites

### CRIT-07: Threat model document missing
**Class:** process / scope foundation
**Source:** ag-sa pass-2 #5
**Issue:** 40 findings приоритизируются без основы — нет ответа "от кого защищаемся".
**Fix:** 1 страница `docs/security/threat-model.md` — 4 пункта: assets (что защищаем), actors (кто атакует), trust boundaries, abuse cases. После — переоценка всех findings.

---

## P1 — High priority

### HIGH-08: forward_lookup exact-text identification primitive
**Source:** codex pass-1 #1
**File:** `bot/handlers/forward_lookup.py:58-65`
**Issue:** идентификация автора по точному совпадению текста — duplicated/common text вернёт wrong member's intro to authorized requester (privacy leak between members).
**Fix:** использовать stored sender metadata (`forward_origin` from message attribution), не exact-text lookup.

### HIGH-09: N2 missing legacy intro_text backfill
**Source:** codex pass-1 #2
**Files:** `bot/__main__.py:77-80`, `bot/handlers/forward_lookup.py:76-80`
**Issue:** N2 предположил storage invariant "intro_text всегда render-ready". Legacy rows предшествовавшие N2 — raw HTML без escape. Forward_lookup на legacy intros = either garbled или XSS.
**Fix:** alembic migration: backfill `intros.intro_text` через `html_escape` для всех rows.

### HIGH-10: Cookie secure=True missing
**Source:** codex pass-1 #4
**File:** `web/routes/auth.py:37-43`
**Issue:** admin session cookie без `secure=True` flag. Если хоть когда-нибудь HTTP fallback — cookie уйдёт в plaintext.
**Fix:** `secure=True, httponly=True, samesite='strict'`. После Tailscale-only switch (handoff coolify-tailscale-only) cookie всегда over Tailscale-encrypted, но secure=True должен быть anyway.

### HIGH-11: pg_dump = fake disaster recovery
**Source:** ag-partner #3 + ag-sa #4 + ag-sa #1.4
**Issue:** dump на том же `/dev/sda1` что DB; нет offsite (S3/B2); нет encryption at rest; ни разу не запускался restore drill; нет alert на 0-byte/missing dump.
**Fix:** restic/borg → B2 с client-side age encryption; restore drill раз в квартал; sentinel watchdog на last_run_ts + alert.

### HIGH-12: No feedback loops anywhere
**Source:** ag-sa pass-1 #8
**Issue:** ни один из 14 fix'ов не имеет post-deploy verification в проде. N1 default password — нет alert на login attempts; H2 chat_messages — нет метрики "messages rejected"; W1 hmac — нет log "session validation failed"; B1 sheets TTL — нет hit/miss метрики; pg_dump — log на VPS никто не читает.
**Fix:** минимальный health-script (cron на ноуте, раз в день): probe Tailscale, Coolify reach, last pg_dump <30h && >100KB, GHCR PAT expiry >30d, alembic_version match. Одна строка в Telegram founder'у.

### HIGH-13: Operator burden — 8+ ритуалов без автоматики
**Source:** ag-sa pass-1 #9
**Tasks** (никто не записан в календарь):
- ротация GHCR PAT (90 дней)
- ротация Coolify token (now urgent, see CRIT-05)
- regen `requirements.lock` (when?)
- regen WEB_SESSION_SECRET (now urgent)
- обновление Hostinger token
- pg_dump restore drill (квартально)
- ротация Tailscale auth keys
- rollback drill
- review FW
**Fix:** dependabot + scheduled GitHub Actions с reminder через Telegram. Single source: `docs/ops/rotation-calendar.md` + cron jobs.

### HIGH-14: requirements.lock без CVE update process
**Source:** ag-partner #5
**Issue:** lock замораживает deps на 27.04. Security приходит через CVE patches — lock блокирует. Нет dependabot, нет regen process.
**Fix:** GitHub Dependabot config — weekly auto-PR на pip dependencies. Auto-merge if CI green.

### HIGH-15: CI gates без owner / SLA / response runbook
**Source:** ag-partner #4 + ag-sa #5
**Issue:** trivy / semgrep findings — кто реагирует, в какие сроки, что делать с false positives? Через 2 недели "continue-on-error: true" = security theater.
**Fix:** runbook `docs/ops/ci-security-response.md` — на каждый gate: owner, SLA, false-positive процедура, escalation.

### HIGH-16: Cross-team conflict через 30 дней (memory team T0/T1)
**Source:** ag-sa pass-2 #2
**Specific collision points:**
- `WEB_SESSION_SECRET` validation vs forward sessions — `bot/web/app.py`
- Rate limit middleware vs ingestion runs — `bot/web/middleware.py` + `bot/services/ingestion.py`
- `update_id` schema vs vouch batching — `bot/db/models.py`
**Fix:** shared invariant document `docs/contracts/shared-files.md` — для каждого "горячего" файла: что обещает, что нельзя ломать.

---

## P1 — Process / methodology

### MID-17: Open-loop control pattern (9/40 findings)
**Source:** ag-sa pass-2 #1 (mode-of-failure)
**Pattern:** артефакт создан (код / документ / mount / token / backup) и засчитан как защита, без обратной связи "работает ли он на самом деле". Cybernetically: open-loop control → drift до катастрофы.
**Systemic fix:** правило процесса — каждый CI gate / mount / backup / rate limit / security review требует обязательную пару (probe, owner, SLA) до merge.

### MID-18: Process antipattern — мы повторили шаблон 75567d36
**Source:** ag-sa pass-2 #3 + meta
**Symptoms прямо сейчас:**
- pass 1 findings без raw evidence (P1 нарушено)
- prompts > 200 строк (P4)
- reviewer'ы углубляются монотонно без falsification step
- нет user-in-the-loop pre-dispatch sync (P3)
**Fix:** sentinel pre-dispatch checklist — нельзя dispatch reviewer без (а) success criteria от user, (б) raw evidence requirement в промпте, (в) cap 200 строк промпта, (г) falsification step в выводе.

### MID-19: N3 vouch flooding via filling state
**Source:** partner #8 + codex отсутствует прямой
**Issue:** теперь timer от submitted_at (не created_at) → юзер может застрять в filling state бесконечно. Где TTL на filling?
**Fix:** auto-cancel filling apps старше N дней (например 14).

### MID-20: H2 — phantom members в DB не аудированы
**Source:** partner #9
**Issue:** H2 пофиксил путь, но **существующие** `is_member=True` с granted_via неизвестным остались. Аудит не проводился.
**Fix:** SQL `SELECT * FROM users u LEFT JOIN vouch_log v ON v.vouchee_id = u.id WHERE u.is_member=True AND v.id IS NULL` → manual review каждой строки.

### MID-21: Get_or_create_live_run race
**Source:** codex pass-1 #8 (memory team code, but pattern matters)
**File:** `bot/services/ingestion.py:98-109`, migration `004_add_ingestion_runs.py:58-63`
**Fix:** partial unique index for running live run + ON CONFLICT, или `pg_advisory_xact_lock`.

### MID-22: NULL update_id dedupe gap
**Source:** codex pass-1 #9 (memory team code)
**Files:** `bot/db/repos/telegram_update.py:77-90`, `tests/db/test_telegram_update_repo.py:79-101`
**Issue:** synthetic/import updates с update_id=NULL всегда insert; tests blessed это как valid.
**Fix:** unique partial index on `(ingestion_run_id, raw_hash) WHERE update_id IS NULL`.

### MID-23: /healthz exposed без auth + DB pressure
**Source:** codex pass-1 #6
**Files:** `web/routes/health.py:17-20`, `bot/services/health.py:72-75`
**Fix:** split liveness (no DB) vs readiness (with cached check, internal only).

### MID-24: Raw archive fail-open
**Source:** codex pass-1 #7
**File:** `bot/middlewares/raw_update_persistence.py:53-61`
**Fix:** dead-letter queue + alerting когда archive flag enabled.

### MID-25: Offrecord retains content hash
**Source:** codex pass-1 #5
**Files:** `bot/services/ingestion.py:141-158`
**Fix:** keyed HMAC on offrecord, или skip hash entirely.

### MID-26: Dockerfile без hash pinning
**Source:** codex pass-1 #10
**Files:** `Dockerfile.bot:1,13`, `Dockerfile.web:1,13`
**Fix:** pin base image by digest (`python:3.12-slim@sha256:...`); regenerate lock with `--generate-hashes`; install with `pip --require-hashes`.

### MID-27: Phantom legacy rollback path
**Source:** ag-sa pass-1 #6
**Issue:** runbook предлагает rollback на legacy /home/claw, но legacy compose монтирует credentials.json как root, у legacy alembic_version фиксирован на 2026-04-20. **Rollback drill ни разу не проводился**.
**Fix:** либо drill (квартально), либо decommission legacy совсем.

### MID-28: Tailscale без break-glass
**Source:** ag-sa pass-1 #2
**Issue:** Tailscale account suspended / coordination plane outage / MagicDNS поломка → founder теряет доступ ко всему. SSH 22 — ключ с того же Mac.
**Fix:** `docs/runbooks/emergency-no-tailscale.md` — recovery via Hostinger console + emergency SSH key on a USB stick (out-of-band).

---

## P2 — Lower priority

### LOW-29: vaultwarden over-deletion
**Source:** ag-partner #6
**Issue:** удалили целиком, можно было изолировать на 127.0.0.1.
**Fix:** не actionable, deferred.

### LOW-30: N5 sha pin coupling (handoff exists)
**Source:** ag-partner #7
**Status:** в handoff `.handoffs/handoff_2026-04-26_20-05_n5-sha-pin.md`.

### LOW-31: H7 semgrep ruleset не custom-tuned
**Source:** partner #4
**Issue:** default rules ловят тупые ошибки, пропускают real bugs (ORM injection через f-string).
**Fix:** custom semgrep rules для bot/ — отдельный sprint, не критично.

### LOW-32: Strategic blind spot — single-admin baked into infra
**Source:** ag-partner blind spot #1
**Issue:** Tailscale-only / single password / no MFA — работают потому что admin = founder = 1 человек. Когда придёт второй админ, инфра развалится.
**Fix:** не сейчас, но note в roadmap.

### LOW-33: Strategic blind spot — review process не починен
**Source:** ag-partner blind spot #2 + ag-sa pass-2 meta
**Fix:** см. MID-18 — sentinel pre-dispatch checklist.

---

## Top 3 Most Dangerous Right Now (executive)

| # | What | Why first |
|---|---|---|
| 1 | Operator security split (CRIT-06): YubiKey for git, separate Tailscale identity for VPS, 1Password admin vault | One-step kill chain — без этого всё остальное косметика |
| 2 | Threat model 1-page doc (CRIT-07) | После него половина из 40 findings re-rank — некоторые окажутся неактуальны |
| 3 | Fix P0 prod bugs (CRIT-01, 02, 03 — bypass vouching, ghost invites, race) | Без них бот ломается через социальную инженерию за 5 минут |

---

## Synthesis

40 findings распадаются на 4 mode-of-failure:
1. **Business-logic + race** (CRIT-01, 02, 03) — самые критичные, ломают весь смысл бота.
2. **Operator-induced leaks** (CRIT-05, 06, partner #10) — основной класс инцидентов в истории проекта (3 раза за 4 дня), системного gate нет.
3. **Open-loop control** (9 findings) — артефакты без feedback loop, drift до катастрофы.
4. **Process antipattern** (MID-17, 18) — мы повторили шаблон 75567d36 в этом самом review.

Этот review — **работа на 30%, ритуал на 70%** (ag-sa pass-2 honest meta). Нет evidence для большинства findings, нет falsification step. **Перед реализацией CRIT'ов нужно user pre-sync**: какие из 33 issue user считает приоритетными, и каков success criterion для каждого.
