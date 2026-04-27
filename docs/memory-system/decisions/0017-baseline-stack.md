# ADR-0017: Baseline stack для memory cycle

- **Status**: Accepted
- **Date**: 2026-04-27
- **Decision-makers**:
  - @Jekudy — product / architecture owner
  - @&lt;tech-lead-handle&gt; — implementation owner (TODO: заменить когда tech lead появится)
- **Author**: GPT-5.5 Pro / principal architect draft
- **Reviewers**: @&lt;collaborator-handle&gt; (TODO: добавить при онбординге)

## Context

Memory cycle стартует поверх существующей кодовой базы Shkoderbot, не с greenfield.
Стек уже сложился (см. `pyproject.toml`), но нигде формально не зафиксирован как
архитектурная база. Без явной ADR коллаборатор может предложить альтернативу (Django,
SQLAlchemy sync, Redis как primary store, Kafka и т. п.) на каждом sprint, и обсуждение
будет повторяться.

ADR фиксирует **что уже принято и не пересматривается** в рамках текущего цикла, и **что
явно отложено**. Это не «новая архитектура» — это свидетельство о текущей реальности +
boundaries для будущего.

## Decision

### Принято и используется

- **Bot runtime**: aiogram >= 3.25 (Telegram bot framework)
- **Admin web**: FastAPI >= 0.115 + Jinja2 + uvicorn
- **Data layer**: SQLAlchemy 2.0 async + asyncpg (Postgres driver)
- **Migrations**: Alembic >= 1.14, additive-first (см. ADR-0011)
- **Database (production)**: Postgres (см. ADR-0001, ADR-0010)
- **Database (dev/test)**: SQLite через aiosqlite (только тесты, dialect-safe repos; см. ADR-0010)
- **Configuration**: pydantic-settings >= 2.0 + python-dotenv
- **Scheduler**: APScheduler >= 3.10 (in-process, не отдельный воркер)
- **HTTP client**: httpx >= 0.28
- **Session signing / web security**: itsdangerous, python-multipart
- **Google Sheets integration**: gspread + gspread-asyncio + google-auth (legacy admin surface)
- **Redis**: только как FSM/queue store если будет явно добавлено (сейчас на `redis>=5.0` зависимость есть, но primary роль — derived/cache, не source of truth)
- **Python**: >= 3.12

### Test stack

- pytest >= 8.3, pytest-asyncio >= 0.24, asyncio_mode = "auto"
- aiosqlite >= 0.20 — **dev-only**, тесты с in-memory sqlite isolation
- ruff >= 0.11, line-length 100, target-version py312

### Ops stack (отдельная extra)

- Telethon >= 1.39 — для Telegram Desktop import dry-run / apply (см. ADR-0012)

### Что отложено / не принято

- **Graph DB (Neo4j / Graphiti)** — отложено, derived-only. См. ADR-0005.
- **Отдельный векторный store (Pinecone, Weaviate, Qdrant)** — отложено. pgvector как
  postgres-native derived index (см. ADR-0014).
- **Kafka / event bus** — отложено. См. ADR-0018 (postgres rows + worker jobs).
- **Butler action layer** — отложено по дизайну (Phase 12), не реализуется до проверки
  governance/review/source-trace в production.
- **Public wiki UI** — отложено (invariant 10).

## Consequences

### Positive

- Любое предложение «давай переедем на X» отвечается ссылкой на ADR-0017 и требует
  отдельного RFC + supersede этого ADR.
- Коллаборатор сразу видит что уже выбрано и работает, не тратит sprint на «давай
  выберем framework».
- Зависимости версионированы в `pyproject.toml`, ADR — мета-уровень обоснования.

### Negative / Trade-offs

- Зафиксированный стек снижает гибкость: переход на Django потребует supersede ADR + 
  serious justification.
- Часть зависимостей (gspread, APScheduler) — legacy от gatekeeper-эры; пересмотр их роли
  в memory-эпоху отложен до момента когда они реально мешают.
- Redis как «опциональный» создаёт неопределённость: зависимость в манифесте есть, primary
  роль не определена. Уточнение — отдельный ADR при первом конкретном use case.

## Alternatives considered

1. **SQLAlchemy sync + threading** — отвергнуто: aiogram async-first; sync блокирует loop.
2. **Tortoise ORM / Django ORM** — отвергнуто: SQLAlchemy 2.0 async уже работает; миграция
   только увеличит surface bugs.
3. **Pydantic v1** — отвергнуто: pydantic-settings v2 уже выбрана; v1 deprecated.
4. **Aiogram 2.x** — отвергнуто: aiogram 3.x — текущий major; обратной совместимости нет.
5. **Celery / RQ для background jobs** — отвергнуто на старте: APScheduler in-process
   достаточен для memory cycle Phase 0–7. Перейти к Celery/RQ — отдельный ADR при росте
   нагрузки.
6. **PostgreSQL JSONB как replacement для отдельных таблиц** — рассмотрено, отвергнуто:
   `message_version` имеет реляционную структуру, JSONB только для derived данных
   (extraction candidates, observations).

## References

- `pyproject.toml` — canonical список зависимостей и версий
- HANDOFF.md §0 «What exists today», §1 implementation strategy
- ADR-0001 — Postgres as source of truth
- ADR-0005 — Graph as projection, not truth
- ADR-0010 — Postgres production, sqlite dev/test only
- ADR-0011 — Additive migrations, durable tombstones
- ADR-0014 — pgvector as derived index
- ADR-0018 — Eventing strategy (postgres rows, no Kafka)
