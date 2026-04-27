# ADR-0018: Eventing strategy — postgres rows + worker jobs (no event bus)

- **Status**: Accepted
- **Date**: 2026-04-27
- **Decision-makers**:
  - @Jekudy — product / architecture owner
  - @&lt;tech-lead-handle&gt; — implementation owner (TODO: заменить когда tech lead появится)
- **Author**: GPT-5.5 Pro / principal architect draft
- **Reviewers**: @&lt;collaborator-handle&gt; (TODO: добавить при онбординге)

## Context

Memory cycle вводит несколько асинхронных pipeline:
- **ingestion**: Telegram update → raw archive → normalization → message_version
- **extraction** (Phase 5): message_version → extraction_candidates
- **summarization** (Phase 7–8): batch → daily/weekly digest
- **search index** (Phase 4): message_version → pgvector embedding refresh
- **import** (Phase 2a/2b): export.json → synthetic telegram_updates → normal pipeline (см. ADR-0012)

Возникает соблазн ввести event bus (Kafka, NATS, RabbitMQ) или Celery с Redis broker.
Это даст «настоящую» асинхронность, retry semantics, dead letter queue, distributed
workers. Но ценой: отдельный сервис, операционная сложность, новая failure mode (broker
down → весь pipeline стоит), новые observability challenge (где сообщение?), новые
security boundary (broker auth).

Для community-бота с одним инстансом и < 10k активных пользователей это over-engineering.
Postgres сам по себе предоставляет durability, transaction semantics, и через `SELECT
... FOR UPDATE SKIP LOCKED` работает как distributed queue без отдельного broker.

## Decision

На фазах 0–7 memory cycle событийность реализуется через postgres-таблицы + idempotent
worker jobs. Никакого внешнего event bus, никакого Celery с Redis broker.

### Архитектурные правила

1. **Raw `telegram_updates` — source log, не async bus.**
   `telegram_updates` хранит сырой Telegram update как append-only лог для replay,
   но не используется как pub/sub канал. Нормализация читает её через explicit cursor
   + `last_processed_update_id` (см. ADR-0012).

2. **Состояние пайплайна — через статусы в postgres-таблицах.**
   Каждая запись имеет `status` (e.g. `pending` / `processing` / `done` / `failed`) и
   `attempt_count` / `last_attempt_at` / `last_error`. Worker берёт работу через
   `SELECT ... FOR UPDATE SKIP LOCKED ... WHERE status = 'pending' LIMIT N`.

3. **Idempotency keys обязательны.**
   Каждая операция (нормализация, extraction, embedding, import apply) имеет explicit
   idempotency key (`message_id` + `content_hash`, `import_batch_id` + `source_message_id`,
   etc.). Повторный запуск с тем же ключом не создаёт дубликатов.

4. **`ingestion_runs` — audit trail для batch-операций.**
   Каждый прогон ingestion / import / extraction регистрируется как row с input/output
   counts, начальным offset, конечным offset, статусом. Failure модно replay.

5. **Worker jobs — APScheduler in-process.**
   Используется текущий APScheduler (см. ADR-0017). Один процесс, fixed cron schedules,
   простая модель. Отдельные worker-процессы — отложено до появления реальной потребности.

6. **`outbox pattern` где это уместно.**
   Для операций, которые меняют DB **и** отправляют исходящий сигнал (e.g. notify admin
   через Telegram, write to Google Sheets), использовать outbox table: запись в outbox в
   той же transaction, что DB update; отдельный worker читает outbox и выполняет side
   effect с retry.

### Будущая возможность ввести queue

Не запрещено вводить Celery / RQ / отдельный worker процесс позже, если:
- Один инстанс перестаёт справляться (CPU, memory)
- Latency-critical operations требуют немедленной обработки
- Нужен pub/sub fan-out на multiple consumers

Это будет отдельный ADR (supersede данный) с конкретным trigger metric.

## Consequences

### Positive

- Один process, один deployment artifact, один observability target.
- Postgres транзакционность гарантирует «не потеряли событие при падении».
- Replay тривиален: SQL update + worker tick.
- Locally воспроизводится без поднятия Kafka/Redis/брокера.
- Idempotency keys явные и аудируемые.

### Negative / Trade-offs

- При высокой нагрузке `SELECT FOR UPDATE SKIP LOCKED` создаёт row-level locks → throughput
  ограничен Postgres connection pool.
- Один inst процесс = SPOF. Нет автоматического failover до явного перехода на multi-worker.
- APScheduler in-process падает вместе с ботом → cron-задачи пропускаются. Нужен
  monitoring + alert на failed runs.
- Outbox pattern требует discipline: легко забыть про него и сделать side effect напрямую.
- Замер latency ingestion → message_version разрезается по APScheduler tick rate (полминуты-минута),
  не millisecond. Если потребуется realtime — нужен переход.

## Alternatives considered

1. **Kafka / Redpanda + consumers** — отвергнуто: операционная сложность не оправдана
   текущей нагрузкой. Будет рассмотрено если ingestion rate > 10 msg/sec sustained.
2. **Celery + Redis broker** — отвергнуто: Redis уже есть в зависимостях, но primary роль
   не определена; добавлять Celery усложнит deployment без явной выгоды.
3. **NATS / RabbitMQ** — отвергнуто: те же аргументы.
4. **Postgres LISTEN/NOTIFY как pub/sub** — отвергнуто на старте: NOTIFY не durable,
   слушатель должен быть live. Может быть добавлено позже как low-latency hint поверх
   row-based polling.
5. **Отдельные worker-процессы (без broker)** — рассмотрено, отложено: APScheduler
   in-process достаточен для Phase 0–7. Переход к отдельным worker — отдельный ADR.

## References

- HANDOFF.md §1 «critical path», §2 phase 5/7/8
- ADR-0007 — Import through same governance
- ADR-0011 — Additive migrations, durable tombstones
- ADR-0012 — Telegram import via synthetic updates
- ADR-0017 — Baseline stack (APScheduler, no Celery on bootstrap)
- [Postgres docs — SELECT FOR UPDATE SKIP LOCKED](https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE)
