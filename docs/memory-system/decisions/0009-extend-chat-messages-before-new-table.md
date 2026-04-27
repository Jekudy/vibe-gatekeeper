# ADR-0009: Расширять `chat_messages` перед введением новых таблиц сообщений

- **Status**: Accepted
- **Date**: 2026-04-27
- **Decision-makers**:
  - @Jekudy — product / architecture owner
  - @<tech-lead-handle> — implementation owner (TODO: заменить когда tech lead появится)
- **Author**: GPT-5.5 Pro / principal architect draft
- **Reviewers**: @<collaborator-handle> (TODO: добавить при онбординге)

## Context

В текущем репо `chat_messages` хранит минимальный набор полей: `id`, `message_id`,
`chat_id`, `user_id`, `text`, `date`, `raw_json`, `created_at`. Этого недостаточно для
memory-системы: нет `reply_to_message_id`, `message_thread_id`, `caption`, `message_kind`,
`memory_policy`, метаданных вложений и ссылок.

Возникает развилка: создать новую таблицу сообщений параллельно со старой (с богатой
схемой), или расширить существующую `chat_messages` аддитивно.

Создание второй таблицы сообщений влечёт:
- Два источника данных об одном и том же сообщении (нарушение ADR-0001)
- Необходимость синхронизации между таблицами или миграции данных
- Риск того, что старый гейткипер-код работает с одной таблицей, а memory-код с другой
- Усложнение JOIN'ов и governance-проверок (tombstone должен применяться к обеим?)

В текущем цикле (Phase 0–1) новые колонки должны добавляться осторожно: без NOT NULL
без DEFAULT, с backfill для существующих строк, без нарушения работы гейткипера.

## Decision

`chat_messages` остаётся единственной normalized message table на Phase 0–1.
Таблица расширяется аддитивно, новая параллельная messages-таблица не создаётся.

Конкретные правила:

1. **Extend, не replace.** Все новые поля добавляются в `chat_messages` как nullable
   колонки или с DEFAULT. Никакой "v2 messages table" в этом цикле.
2. **Backfill для NOT NULL**: если нужна NOT NULL колонка — сначала `ALTER TABLE ADD COLUMN NULL`,
   потом backfill, потом `ALTER TABLE ALTER COLUMN SET NOT NULL`. Никогда в один шаг.
3. **`memory_policy` backfill**: при добавлении поля `memory_policy` — backfill значением
   `'normal'` для всех существующих строк (они не помечались `#nomem`/`#offrecord`).
4. **`message_versions`** — это новая таблица (Phase 1), но она не заменяет `chat_messages`.
   Она дополняет: версии ссылаются на `chat_messages` через FK.
5. **Параллельные legacy-пути**: код, читающий `chat_messages` в gatekeeper (vouch, lookup),
   не требует изменений при добавлении новых колонок благодаря NULL-default стратегии.

### Авторизованные колонки для расширения (Phase 1, тикет T1-05)

Nullable / с DEFAULT, не нарушают существующие rows:
- `reply_to_message_id` (BIGINT, NULLABLE)
- `message_thread_id` (BIGINT, NULLABLE)
- `caption` (TEXT, NULLABLE)
- `message_kind` (VARCHAR, DEFAULT `'text'`)
- `memory_policy` (VARCHAR, DEFAULT `'normal'`, backfill required)
- `is_redacted` (BOOLEAN, DEFAULT FALSE)
- `ingestion_run_id` (FK к `ingestion_runs`, NULLABLE)

## Consequences

### Положительные

- Единая таблица сообщений: governance (tombstone, policy) применяется в одном месте.
- Гейткипер-код не требует изменений после добавления nullable колонок.
- JOIN-ы остаются простыми: нет необходимости в UNION или cross-table refs для одного сообщения.
- Rollback через code revert не требует data-migration.

### Отрицательные / компромиссы

- Таблица со временем становится широкой — требует disciplined schema evolution.
- NULL-значения для всех legacy строк требуют NULL-safe обработки в коде.
- Некоторые оптимизации (партиционирование, sharding) сложнее с монолитной таблицей.
- TODO: архитектор должен определить момент, когда `chat_messages` пора нормализовать
  (вынести metadata в отдельные таблицы) — это Phase 5+ решение.

## Alternatives considered

| Вариант | Почему отклонён |
|---------|-----------------|
| Создать `memory_messages` параллельно с `chat_messages` | Два источника данных об одном сообщении; нарушение ADR-0001; синхронизация сложна |
| Дропнуть `chat_messages` и создать новую | Breaking migration; ломает гейткипер; неприемлемо до Phase 5+ |
| Вынести память в отдельный сервис со своей БД | Overengineering; нарушает принцип единого Postgres как источника истины (ADR-0001) |
| Создать view поверх `chat_messages` | View не решает проблему хранения данных; не даёт write-пути |

## References

- [HANDOFF.md §1 — strategy](../HANDOFF.md): "`chat_messages` is extended, not replaced"
- [HANDOFF.md §6 — global migration rules](../HANDOFF.md): "`chat_messages` stays canonical normalized message table early on"
- [HANDOFF.md §5 — ticket T1-05](../HANDOFF.md): extend chat_messages fields
- [ADR-0001](0001-postgres-as-source-of-truth.md) — единый источник истины
- [ADR-0008](0008-preserve-gatekeeper-during-migration.md) — additive migrations для сохранения гейткипера
- [ADR-0011](0011-additive-migrations-tombstones-durable.md) — стратегия additive migrations
