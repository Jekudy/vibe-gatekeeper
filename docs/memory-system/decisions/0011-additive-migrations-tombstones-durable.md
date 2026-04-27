# ADR-0011: Аддитивные миграции сначала; tombstone'ы долговечны и не откатываются просто так

- **Status**: Accepted
- **Date**: 2026-04-27
- **Decision-makers**:
  - @Jekudy — product / architecture owner
  - @<tech-lead-handle> — implementation owner (TODO: заменить когда tech lead появится)
- **Author**: GPT-5.5 Pro / principal architect draft
- **Reviewers**: @<collaborator-handle> (TODO: добавить при онбординге)

## Context

При построении memory-системы поверх существующего гейткипера необходимо определить
стратегию эволюции схемы БД. Два принципа формируют эту стратегию:

**Принцип 1 — аддитивные миграции.**
Ранние фазы (0–1) затрагивают живую БД с реальными участниками. Breaking migration
(drop column, rename, change type) ломает работающий код до деплоя новой версии.
Нет окна обслуживания — бот должен работать непрерывно.

**Принцип 2 — tombstone'ы долговечны.**
`forget_events` реализует right-to-forget: участник просит удалить своё сообщение.
Если tombstone можно легко откатить (casual rollback), то право забвения становится
иллюзорным. Существует риск: "давай откатим миграцию tombstone'ов, они мешают" — это
недопустимо.

Эти два принципа влияют на разные части жизненного цикла схемы и поэтому оформлены
совместно в одном ADR.

## Decision

### Аддитивные миграции

1. **ADD COLUMN, не DROP/RENAME/CHANGE TYPE.** В Phase 0–2 все изменения таблиц —
   только добавление колонок. Дроп deprecated колонок — отдельный ADR после Phase 3+,
   когда убеждены что ничего не сломает.
2. **NOT NULL без DEFAULT запрещён на populated таблицах.** Процесс: `ADD COLUMN NULL` →
   backfill в отдельном шаге → `SET NOT NULL`. Никогда одним шагом на production data.
3. **Каждая миграция должна иметь тикет.** Нет тикета — нет миграции. Это защищает от
   scope creep и "давай заодно добавим колонку".
4. **Derived layers ребилдируемы** — их можно дропнуть и пересоздать из Postgres.
   Это позволяет делать более агрессивные операции с derived-таблицами (фаза 5+).

### Tombstone'ы долговечны

5. **`forget_events` — append-only.** Tombstone создаётся, но не удаляется. Обновляется
   только статус (`pending` → `processing` → `completed`/`failed`). Строки из `forget_events`
   не CASCADE-удаляются при delete других сущностей.
6. **Forget не откатывается.** После создания tombstone нет команды "undo forget".
   Если нужно восстановить контент — это отдельный admin action с аудитом, не rollback.
7. **Tombstone выживает при code rollback.** Если катим назад код Phase 3 — tombstone-строки
   в БД остаются. Код нового деплоя обязан проверять `forget_events` при re-import и extraction.
8. **Tombstone multi-key.** Одно событие забвения может соответствовать нескольким ключам:
   `message:<chat_id>:<message_id>`, `message_hash:...`, `user:<telegram_user_id>`,
   `export:<source>:<export_message_id>`. Это защищает от resurrection при import.

## Consequences

### Положительные

- Аддитивные миграции позволяют zero-downtime deploy.
- Code rollback не требует data rollback — миграцию не нужно откатывать.
- Tombstone durability даёт реальные гарантии right-to-forget.
- Append-only forget_events упрощает audit trail.

### Отрицательные / компромиссы

- Таблицы накапливают "мёртвые" колонки; нужна периодическая schema cleanup (Phase 5+).
- NOT NULL с backfill — три шага вместо одного; медленнее на больших таблицах.
- Невозможность undo forget создаёт риск ошибочного forget без recovery; требует
  чёткой авторизации (ADR-0003, Phase 3).
- Tombstone-строки занимают место даже для "давно забытого" контента.

## Alternatives considered

| Вариант | Почему отклонён |
|---------|-----------------|
| Breaking migrations с maintenance window | Нет возможности maintenance window; бот должен работать непрерывно |
| Soft-delete вместо tombstone (is_deleted флаг) | Soft-delete легко откатить; нет multi-key защиты от resurrection через import |
| Tombstone с TTL (автоочистка через N дней) | Нарушает right-to-forget; forgot через 1 год тоже должен защищать от resurrection |
| Event sourcing (всё как события, миграции не нужны) | Overengineering для текущего масштаба; несовместимо с существующей gatekeeper схемой |

## References

- [HANDOFF.md §1 — invariant 9](../HANDOFF.md): "Tombstones are durable and not casually rolled back"
- [HANDOFF.md §6 — global migration rules](../HANDOFF.md): "Early migrations are additive; Tombstones are durable"
- [HANDOFF.md §10 — forget_events](../HANDOFF.md): tombstone keys, append-only strategy
- [ADR-0003](0003-offrecord-irreversibility.md) — необратимость offrecord и forget
- [ADR-0008](0008-preserve-gatekeeper-during-migration.md) — additive migrations для сохранения гейткипера
