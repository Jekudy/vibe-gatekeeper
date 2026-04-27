# ADR-0005: Граф — проекция из Postgres, не источник истины

- **Status**: Accepted
- **Date**: 2026-04-27
- **Decision-makers**: TODO — уточни у архитектора

## Context

В Phase 10 планируется граф знаний (Neo4j/Graphiti) для traversal-запросов: "кто знает X",
"как связаны понятия A и B", "какие события предшествовали Y". Граф предоставляет
возможности, которых нет у реляционной БД.

Возникает вопрос о природе этого графа: является ли он авторитетным источником данных
или производным объектом? Если граф содержит "факты", которых нет в Postgres (или
противоречащие Postgres), система имеет два конкурирующих источника истины — это
неприемлемо с точки зрения consistency и governance.

Конкретный риск: если `forget`/tombstone применяется в Postgres, но граф не обновляется —
"забытый" контент продолжает быть доступным через graph traversal.

## Decision

Граф (Neo4j/Graphiti) является исключительно derived projection из PostgreSQL.

- Граф строится на основе карточек, событий, связей из Postgres; не имеет собственных
  авторитетных данных.
- Граф пересобирается из Postgres полностью при необходимости (`graph_sync_runs` отслеживает состояние).
- При tombstone/forget: Postgres — первичное место применения; граф обновляется каскадом
  (purge graph) — либо синхронно, либо как часть cascade-воркера.
- Butler (Phase 12, design-only) не читает граф напрямую как источник истины — он получает
  governance-filtered evidence context, который может включать граф-traversal как один из
  инструментов.
- Если граф расходится с Postgres — правда на стороне Postgres, граф пересобирается.

## Consequences

### Положительные

- Forget/tombstone в Postgres автоматически invalidate граф — нет риска воскрешения через graph API.
- Граф можно дропнуть и пересобрать без потери данных.
- Нет split-brain: единственный источник истины, две формы представления.
- Упрощена governance: одна точка enforcement, а не две.

### Отрицательные / компромиссы

- Rebuild графа при большой базе может быть медленным и дорогим.
- Необходимо обеспечить idempotency rebuild — нельзя создавать дубли при частичном rebuild.
- TODO: архитектор должен определить: граф обновляется синхронно с forget (в той же транзакции)?
  Или через async cascade-воркер? Если async — какова допустимая задержка до purge?
- TODO: как обрабатывать graph-запросы во время rebuild? Read-only mode? Старый граф как fallback?

## Alternatives considered

| Вариант | Почему отклонён |
|---------|-----------------|
| Граф как co-equal источник истины (write to both) | Два источника истины → risk divergence, двойная governance нагрузка |
| Граф как единственное хранилище отношений, Postgres как lookup | Граф не имеет transactional гарантий Postgres; forget/tombstone сложнее |
| Отказаться от графа полностью | Теряем traversal-возможности; "кто знает X" без графа — дорогие JOIN'ы |

## References

- [HANDOFF.md §1 — invariant 6](../HANDOFF.md): "Graph is never source of truth"
- [HANDOFF.md §2 — phase 10](../HANDOFF.md): Phase 10 Graphiti/Neo4j, `graph_sync_runs`, rebuild
- [HANDOFF.md §3 — dependency graph](../HANDOFF.md): graph blocked by stable cards/events/relations
- [ADR-0001](0001-postgres-as-source-of-truth.md) — фундаментальное решение о Postgres как источнике
