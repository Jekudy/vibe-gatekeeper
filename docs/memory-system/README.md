<!-- Root: ~/Vibe/CLAUDE.md — ALWAYS read it first for vault-wide rules and structure -->

# Shkoderbot Memory System — Documentation

This directory holds the canonical specification and roadmap for the Shkoderbot memory system —
the migration from a pure community gatekeeper into a governed community memory.

## Project Origin

Архитектура системы памяти спроектирована AI-архитектором (ChatGPT 5.5 Pro) за 5 промптов
в апреле 2026. Прямой вывод той сессии лежит в `HANDOFF.md` (~1200 строк, canonical).

Документы `ARCHITECTURE.md`, `GLOSSARY.md` и `decisions/*.md` (ADR) — это **пост-обработка**
вывода архитектора для онбординга людей и коллабораторов: HANDOFF слишком плотный для первого
знакомства. Если ADR/ARCHITECTURE противоречат HANDOFF — побеждает HANDOFF (он canonical),
а ADR/ARCHITECTURE правятся. Если правки в HANDOFF — обязательно обновить связанные ADR.

Новые архитектурные решения, не вошедшие в исходный HANDOFF, оформляются как новые ADR
в `decisions/` через RFC в GitHub Discussions → accept → ADR + связанный issue.

## Read order (15-minute onboarding first, details later)

0. `ONBOARDING.md` — **если ты новый коллаборатор**, начни здесь. 30-минутный путь от нуля до "могу взять тикет".
1. `ARCHITECTURE.md` — система целиком: компоненты, поток данных, mermaid-диаграмма, что куда не ходит.
2. `GLOSSARY.md` — термины: message_version, tombstone, #offrecord, evidence card, llm_gateway и др.
3. `decisions/` — ADR (Architecture Decision Records): почему сделано именно так. Начни с ADR-0001.
4. `ROADMAP.md` — 12 фаз, gates, что авторизовано сейчас, что заблокировано и чем.
5. `AUTHORIZED_SCOPE.md` — точный список тикетов, авторизованных в текущем цикле. Critical safety rule для `#offrecord`.
6. `IMPLEMENTATION_STATUS.md` — что реализовано vs запланировано. Статус каждого тикета. Обновляется после каждого PR.
7. `DEV_SETUP.md` — как запустить dev bot локально с изолированным dev postgres.
8. `HANDOFF.md` — canonical detailed spec (1200+ строк). Читай после первых семи — как reference, а не как введение.

## Source of truth

If a previous spec disagrees with `HANDOFF.md`, `HANDOFF.md` wins. The legacy v0.5 design spec
(`docs/superpowers/archive/2026-04-22-shkoderbot-memory-editor-design.SUPERSEDED.md`) is
superseded — do not implement from it.

## Workflow

- Branch: `feat/memory-foundation` in worktree `.worktrees/memory/`.
- Framework: superflow (per-worktree state file, does not collide with the main `security-audit`
  cycle running on `main`).
- Issue tracker: GitHub Issues. Labels: `phase:0`, `phase:1`, `area:memory`,
  `area:gatekeeper-safety`, `area:db`, `area:governance`, `area:ingestion`.
- PR target: `main`. Sprint-PR-queue mode (one PR per ticket, sequential rebase, CI green before
  merge).
- Reviewers per PR: Claude product reviewer + Codex technical reviewer (dual review). Codex used
  for migrations and security-sensitive code.
- Documentation: every merged PR updates `IMPLEMENTATION_STATUS.md`.

## Workflow для архитектурных решений

```
Discussions/RFC → ADR → Issue → PR
```

1. Новое архитектурное предложение → GitHub Discussions, категория `RFC`.
2. После accept → создаётся ADR в `decisions/`.
3. ADR → создаётся implementation issue с link на ADR.
4. Issue → PR с link на issue (PR template требует ADR-ссылку для sensitive paths).

### Discussions vs Issues

- **Discussions / RFC** — new architecture, change to invariants, source-of-truth/governance changes, retention/privacy policy, llm/extraction policy, public wiki decision, graph/butler decision, schema strategy changes.
- **Issues** — implementation tickets, bugs, small tactical changes, test failures, migration tasks after ADR accepted.

См. ADR-0016 (github governance) для деталей по CODEOWNERS, branch protection, ADR-link check.

## Non-negotiable invariants (from HANDOFF.md §1)

1. Existing gatekeeper must not break.
2. No LLM calls outside `llm_gateway`.
3. No extraction/search/qa over `#nomem` / `#offrecord` / forgotten content.
4. Citations point to `message_version_id` or approved card sources.
5. Summary is never canonical truth.
6. Graph is never source of truth.
7. Future butler cannot read raw DB directly; must use governance-filtered evidence context.
8. Import apply must go through the same normalization/governance path as live updates.
9. Tombstones are durable; not casually rolled back.
10. Public wiki disabled until review/source-trace/governance proven.
