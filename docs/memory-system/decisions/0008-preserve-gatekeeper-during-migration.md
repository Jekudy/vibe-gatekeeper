# ADR-0008: Гейткипер должен оставаться рабочим в процессе миграции

- **Status**: Accepted
- **Date**: 2026-04-27
- **Decision-makers**:
  - @Jekudy — product / architecture owner
  - @<tech-lead-handle> — implementation owner (TODO: заменить когда tech lead появится)
- **Author**: GPT-5.5 Pro / principal architect draft
- **Reviewers**: @<collaborator-handle> (TODO: добавить при онбординге)

## Context

Shkoderbot сейчас выполняет критическую роль гейткипера комьюнити: приём заявок,
vouching, intro refresh, Google Sheets интеграция, admin dashboard. Это не
экспериментальный код — на нём завязан онбординг реальных участников.

Параллельно начинается многофазная миграция к governed community memory. Миграция
затрагивает `bot/db/`, `bot/services/`, миграции Alembic, хэндлеры. Существует риск:
разработчик, торопясь добавить Phase 1 таблицы, сломает существующий gatekeeper workflow.

Конкретные зоны риска:
- `chat_messages` — таблица используется и гейткипером, и memory-слоем
- `UserRepo.upsert` — критичный путь онбординга
- `forward_lookup` — показывает intro участников при vouching
- `allowed_updates` — список типов апдейтов бота

Ни одна memory-фича не имеет ценности, если ломает онбординг участников.

## Decision

Существующий гейткипер обязан продолжать работать на каждом шаге миграции.

Конкретные правила:

1. **Ранние миграции — только аддитивные.** Нельзя дропать или переименовывать
   существующие таблицы и колонки. Новые колонки добавляются с `DEFAULT` или `NULL`,
   чтобы старые строки выживали без backfill.
2. **`chat_messages` — не заменяется.** Таблица расширяется (extend), а не заменяется
   новой. Это canonical normalized message table на весь Phase 0–1.
3. **`allowed_updates` — не расширяется без хэндлера.** Нельзя добавить тип апдейта
   (например `edited_message`) пока хэндлер и таблица-получатель не существуют.
4. **Feature flags по умолчанию OFF.** Весь новый memory-код спрятан за feature flag.
   Флаг включается только после того, как PR с ним прошёл тесты.
5. **Regression tests обязательны** для каждого изменения, затрагивающего gatekeeper-пути:
   `forward_lookup`, vouching, `UserRepo.upsert`, onboarding handlers.
6. **Rollback — только через code rollback.** До Phase 3 (governance/tombstones) нет
   деструктивных data-операций; всё обратимо через code revert.

## Consequences

### Положительные

- Онбординг участников работает непрерывно на протяжении всей миграции.
- Additive-only миграции позволяют откат кода без data-потерь.
- Feature flag per phase — можно включать/выключать memory-фичи независимо.
- Чёткая граница: "что трогать нельзя" ясна команде и AI-агентам.

### Отрицательные / компромиссы

- Скорость: нельзя "снести и пересоздать" — каждая миграция требует обратной совместимости.
- Сложность: разработчик должен держать в голове двойной контекст (gatekeeper + memory).
- Некоторые оптимальные схемы недостижимы без breaking migration — принимаем технический долг.

## Alternatives considered

| Вариант | Почему отклонён |
|---------|-----------------|
| Feature-freeze гейткипера на период миграции | Неприемлемо: онбординг реальных людей должен работать |
| Параллельный бот для memory, merge позже | Два кодовых пути расходятся; merge будет болезненным; дублирование кода |
| Migrate-and-cut (одноразовый большой PR) | Слишком высокий риск регрессий; невозможно тестировать инкрементально |
| Заморозить memory до полной готовности гейткипера | Откладывает memory на неопределённый срок; теряем архитектурный импульс |

## References

- [HANDOFF.md §0 — key risks](../HANDOFF.md): "Gatekeeper breakage — Current functionality must survive"
- [HANDOFF.md §1 — invariant 1](../HANDOFF.md): "Existing gatekeeper must not break"
- [HANDOFF.md §1 — strategy](../HANDOFF.md): "Preserve gatekeeper. Early migrations are additive"
- [HANDOFF.md §6 — global migration rules](../HANDOFF.md): "Early migrations are additive"
- [HANDOFF.md §2 — phase 0](../HANDOFF.md): Phase 0 — gatekeeper stabilization, rollback code-only
- [ADR-0011](0011-additive-migrations-tombstones-durable.md) — детали стратегии additive migrations
