# Vibe Gatekeeper VPS Standardization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move `vibe-gatekeeper` from a VPS-only working tree to `GitHub -> GHCR -> Coolify`, while keeping the current production runtime untouched until the new path is ready.

**Architecture:** Import the live VPS working tree into a clean local repository, normalize it for git and CI, publish immutable `bot` and `web` images to GHCR, then install Coolify in parallel and wire a staging deployment from GHCR. The existing production compose stack remains the live path until the new stack is verified.

**Tech Stack:** Python 3.12, aiogram 3, FastAPI, PostgreSQL, Redis, Docker, GitHub Actions, GHCR, Coolify

---

### Task 1: Snapshot and Local Import

**Files:**
- Create: `docs/superpowers/specs/2026-04-12-vps-git-ghcr-coolify-design.md`
- Create: `.agent/tasks/vps-git-ghcr-coolify-bootstrap/spec.md`
- External: `~/Vibe/products/server-snapshots/vibe-gatekeeper-2026-04-12/`

- [x] Confirm a private VPS snapshot exists locally with DB dump, env files, credentials, and runtime metadata.
- [x] Confirm the clean local import exists at `~/Vibe/products/vibe-gatekeeper/`.
- [x] Verify imported working tree does not contain `.env`, `.env.production`, `credentials.json`, or local DB files.

### Task 2: Initialize the Local Repository

**Files:**
- Create: `CLAUDE.md`
- Create: `README.md`
- Modify: `.gitignore`

- [x] Initialize a fresh git repository in `~/Vibe/products/vibe-gatekeeper/`.
- [x] Add a project `CLAUDE.md` with the root reference header and concise repo-specific operating rules.
- [x] Add a `README.md` with:
  - local dev startup
  - `DEV_MODE=true`
  - secret handling rules
  - release model via GHCR
- [x] Tighten `.gitignore` for env files, local snapshots, sqlite DBs, caches, and helper artifacts.

### Task 3: Normalize the Runtime for CI and Image Builds

**Files:**
- Modify: `Dockerfile.bot`
- Modify: `Dockerfile.web`
- Modify: `docker-compose.yml`
- Modify: `pyproject.toml`

- [x] Make sure local build paths are deterministic and do not rely on server-only files.
- [x] Ensure `docker-compose.yml` remains useful for local dev, not as the production deploy mechanism.
- [x] Add any missing dev dependencies needed for repeatable local test execution.

### Task 4: Add CI

**Files:**
- Create: `.github/workflows/ci.yml`

- [x] Add a CI workflow that runs on push and pull request.
- [x] CI must at minimum:
  - install dependencies
  - run tests
  - run lint or static checks
- [x] Keep CI independent from production secrets.

### Task 5: Add GHCR Release Workflow

**Files:**
- Create: `.github/workflows/release.yml`

- [x] Add a release workflow that triggers on `main`.
- [x] Build and push:
  - `ghcr.io/jekudy/vibe-gatekeeper-bot`
  - `ghcr.io/jekudy/vibe-gatekeeper-web`
- [x] Use immutable tags based on commit SHA.
- [x] Optionally maintain stable aliases for `staging` and `prod` only if they do not become the rollback source of truth.

### Task 6: Document Environment Boundaries

**Files:**
- Create: `docs/runbook.md`
- Create: `.env.staging.example`
- Create: `.env.production.example`
- Modify: `.env.example`

- [x] Split documented config into:
  - local dev
  - staging
  - production
- [x] Document which secrets stay outside git.
- [x] Document which settings must differ between staging and production.

### Task 7: Create GitHub Repository and Push

**External Actions:**
- GitHub repo creation
- remote setup
- initial push

- [x] Create a private GitHub repository for `vibe-gatekeeper`.
- [x] Set `origin`.
- [x] Push the normalized local repository.
- [x] Confirm GitHub Actions is enabled and the workflows are visible.

### Task 8: Investigate VPS Constraints for Coolify

**Files:**
- Create: `docs/ops/coolify-preflight.md`

- [x] Inspect current host port usage.
- [x] Inspect existing reverse-proxy consumers.
- [x] Record whether Coolify can claim ports `80` and `443` immediately or needs a staged ingress plan.
- [x] Record any non-Coolify services that must remain host-managed.

### Task 9: Install Coolify in Parallel

**External Actions:**
- VPS install only, no cutover

- [x] Install Coolify without replacing the current `vibe-gatekeeper` production runtime.
- [x] Keep the current compose-managed production stack alive.
- [x] Validate Coolify dashboard access.

### Task 10: Stage GHCR Deployment in Coolify

**Files:**
- Create: `docs/ops/vibe-gatekeeper-staging-cutover.md`

- [ ] Create Coolify resources for staging:
  - app images from GHCR
  - staging database
  - staging Redis
  - staging env
- [ ] Deploy `bot` and `web` from GHCR images.
- [x] Run smoke checks and capture the exact commands/URLs needed for future prod cutover.
  Blocked on GHCR pull access for Coolify on 2026-04-12.

### Task 11: Leave Production Stable

**Files:**
- Modify: `docs/runbook.md`

- [x] Record the old production location and recovery path.
- [x] Do not switch prod in this implementation batch.
- [x] Document the final short stop/start token cutover procedure for the next batch.
