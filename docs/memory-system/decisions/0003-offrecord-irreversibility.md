# ADR-0003: #offrecord — необратимость и атомарная редакция

- **Status**: Accepted
- **Date**: 2026-04-27
- **Decision-makers**:
  - @Jekudy — product / architecture owner
  - @<tech-lead-handle> — implementation owner (TODO: заменить когда tech lead появится)
- **Author**: GPT-5.5 Pro / principal architect draft
- **Reviewers**: @<collaborator-handle> (TODO: добавить при онбординге)
- **Note**: решение имеет юридические и этические последствия; требует явного sign-off от владельца продукта

## Context

Telegram-чаты содержат контент, который участники хотят держать приватным:
личные данные, черновые обсуждения, конфиденциальные решения. Тег `#offrecord`
является явным сигналом от участника "это сообщение не должно попасть в базу знаний".

Проблема: если система сначала сохраняет raw_json целиком, а потом редактирует его
"когда дойдут руки", возникает окно уязвимости — контент физически присутствует
в базе данных в полном виде. Если в этот промежуток произойдёт дамп, утечка или баг,
данные будут скомпрометированы.

Дополнительная проблема: при импорте истории, реимпорте или rebuild derived-слоёв
tombstone/offrecord-маркеры должны блокировать воскрешение уже забытого контента.

## Decision

### Атомарная редакция при сохранении

`#offrecord`-контент **не хранится** в дурабельном виде как raw visible content.

Реализация:
1. `detect_policy(text, caption)` вызывается ВНУТРИ той же DB-транзакции, что сохраняет `telegram_updates`.
2. Если `detect_policy` вернула `'offrecord'` — поля `text`, `caption`, `entities`, `media caption`
   в `raw_json` редактируются (null или sentinel) ДО COMMIT'а.
3. Сохраняются только: `chat_id`, `message_id`, `timestamp`, хэш, tombstone-ключ, policy-маркер,
   audit-метаданные.
4. `offrecord_marks`-строка создаётся в той же транзакции.

До тикета T1-12 в production: raw_json пишется только при включённом feature flag
`memory.ingestion.raw_updates.enabled`, который по умолчанию OFF.

### Необратимость tombstone

- Tombstone (запись в `forget_events`) не удаляется и не отменяется без явного аудита.
- При реимпорте или rebuild derived-слоёв: tombstone-check обязателен до записи.
- Cascade (Phase 3): tombstone распространяется на message_versions, entities, links, FTS,
  vectors, кандидатов, карточки, саммари, граф.
- Forget не является "мягким удалением" — это дурабельный факт о том, что контент запрещён.

### Запрет downstream-доступа

Ни search, ни Q&A, ни extraction, ни summary, ни catalog, ни vector, ни graph, ни LLM
не имеют доступа к `#offrecord`-контенту. `#nomem` аналогично исключается из derived-слоёв,
но raw-данные могут храниться для внутреннего аудита.

## Consequences

### Положительные

- Нет окна уязвимости: контент не попадает в базу в видимом виде.
- Гарантированное соответствие privacy-требованиям участников.
- Cascade предотвращает "воскрешение" через re-import или graph-rebuild.

### Отрицательные / компромиссы

- Порядок тикетов жёстко связан: T1-04 (сырое сохранение) не может мержиться без T1-04 stub для `detect_policy`.
  Это осложняет параллельную разработку.
- Feature flag `memory.ingestion.raw_updates.enabled` обязан оставаться OFF до мержа T1-12 + T1-13.
- Невозможно "отменить" tombstone без явного процесса аудита — это намеренное ограничение,
  но требует осторожности при ошибочных tombstone.
- TODO: архитектор должен прояснить, что происходит с уже сохранёнными legacy `raw_json` до введения детектора.
  Нужен ли ретроспективный скан исторических данных?

## Alternatives considered

| Вариант | Почему отклонён |
|---------|-----------------|
| Сохранять всё, редактировать постфактум | Создаёт окно уязвимости; при утечке данных нарушение уже произошло |
| Не хранить raw_json вообще | Теряем audit trail и возможность дебаггинга; нет idempotency-ключа |
| Мягкое удаление с флагом `is_deleted` | Данные физически остаются в таблице; недостаточно для privacy-требований |
| Асинхронная редакция в воркере | То же окно уязвимости + race condition при сбое воркера |

## References

- [HANDOFF.md §1 — invariant 3](../HANDOFF.md): "No extraction/search/qa over #nomem/#offrecord/forgotten"
- [HANDOFF.md §10 — governance spec](../HANDOFF.md): policy table, #offrecord, #nomem
- [HANDOFF.md §9 — critical ordering rule](../HANDOFF.md): T1-04 ↔ T1-12 cross-cutting requirement
- [AUTHORIZED_SCOPE.md — #offrecord ordering rule](../AUTHORIZED_SCOPE.md)
- [ADR-0004](0004-llm-gateway-as-single-boundary.md) — LLM-граница, комплементарная этому решению
