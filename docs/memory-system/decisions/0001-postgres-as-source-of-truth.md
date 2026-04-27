# ADR-0001: PostgreSQL — единственный источник истины

- **Status**: Accepted
- **Date**: 2026-04-27
- **Decision-makers**:
  - @Jekudy — product / architecture owner
  - @<tech-lead-handle> — implementation owner (TODO: заменить когда tech lead появится)
- **Author**: GPT-5.5 Pro / principal architect draft
- **Reviewers**: @<collaborator-handle> (TODO: добавить при онбординге)

## Context

Исходная база кода использовала SQLite в разработке и PostgreSQL в продакшне.
Это приводило к расхождению поведения: в частности, upsert-операция в `UserRepo`
работала по-разному в зависимости от диалекта, что порождало нестабильные тесты
и риск тихих ошибок в продакшне (тикет T0-02).

Параллельно стояла задача строить систему памяти поверх существующего гейткипера:
хранить raw Telegram-апдейты, версии сообщений, политики приватности, граф знаний.
Для этого нужен один авторитетный источник — без "два хранилища дают два ответа".

## Decision

PostgreSQL является единственным источником истины для всей системы.

- Все данные — raw-архив, нормализованные сообщения, версии, карточки знаний, граф — живут в Postgres.
- В разработке используется изолированный Postgres (docker-compose), не SQLite.
- Граф (Phase 10, Neo4j/Graphiti) — только проекция из Postgres; пересобирается из Postgres при необходимости.
- Derived-слои (саммари, дайджесты, граф, кандидаты) — перестраиваемые, не авторитетные.
- Никакой компонент не может считаться источником истины кроме Postgres.

## Consequences

### Положительные

- Единое место истины: нет расхождения между dev/prod поведением.
- Строгие транзакционные гарантии для `#offrecord`-редактирования (одна транзакция = атомарность).
- Derived-слои можно дропнуть и пересобрать без потери данных.
- Упрощённый rollback: feature flag OFF, derived rows скрыты/удалены, tombstone остаётся.

### Отрицательные / компромиссы

- Разработка требует запущенного Postgres (docker-compose), SQLite-тесты недостаточны.
- Возможные сложности с миграциями при большом объёме данных (backfill требует осторожности).
- Postgres-специфичные запросы (JSONB, upsert ON CONFLICT) нельзя использовать в SQLite-тестах.

## Alternatives considered

| Вариант | Почему отклонён |
|---------|-----------------|
| SQLite в dev + Postgres в prod | Уже приводило к ошибкам (T0-02); диалектные различия upsert — источник скрытых багов |
| Использовать SQLite везде | Не поддерживает нужный уровень concurrency и JSONB-семантику; неприемлемо для production |
| Двойное хранилище (Postgres + граф как co-equal) | Нарушает принцип единого источника истины; граф может расходиться с Postgres |

## References

- [HANDOFF.md §1 — invariant 6](../HANDOFF.md): "Graph is never source of truth"
- [HANDOFF.md §0 — key risks](../HANDOFF.md): "Dev / prod DB mismatch"
- [HANDOFF.md §6 — global migration rules](../HANDOFF.md): "Derived layers are rebuildable"
- [ADR-0005](0005-graph-as-projection-not-truth.md) — следствие этого решения для графа
