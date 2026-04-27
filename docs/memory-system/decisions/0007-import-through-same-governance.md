# ADR-0007: Импорт — через тот же governance-путь, что и live-апдейты

- **Status**: Accepted
- **Date**: 2026-04-27
- **Decision-makers**: TODO — уточни у архитектора

## Context

Telegram Desktop позволяет экспортировать историю чата в JSON-формате. Эта история
содержит тысячи сообщений, среди которых могут быть:
- Сообщения с `#offrecord` или `#nomem` тегами
- Сообщения, уже удалённые пользователем (tombstone в системе)
- Дубликаты сообщений, уже сохранённых через live-ingestion
- Сообщения от пользователей, запросивших `/forget_me`

Если импорт идёт "в обход" governance — напрямую в таблицы — эти сообщения воскреснут
в базе данных как будто ничего не происходило. Это нарушение privacy-гарантий участников
и потенциально серьёзный правовой риск.

Также важно: импорт dry-run (только статистика) безопасен и разрешён раньше,
чем import apply, поскольку не пишет контент в базу данных.

## Decision

Telegram Desktop import apply использует ту же нормализацию и governance-путь,
что и live Telegram-апдейты.

Конкретно:
- Импорт генерирует synthetic `telegram_updates` (искусственные записи в таблице), которые
  далее обрабатываются через `ingestion.py` → `normalization.py` → `governance.py`.
- Пути нет "shortcut": нельзя писать напрямую в `chat_messages` или `message_versions`.
- `detect_policy(text, caption)` вызывается для каждого импортируемого сообщения —
  `#offrecord`/`#nomem` обнаруживается и применяется.
- Tombstone check: перед записью каждого сообщения проверяется `forget_events` по
  tombstone-ключам (`message:<chat_id>:<message_id>`, `message_hash:...`, `user:...`,
  `export:<source>:<export_message_id>`). При совпадении — импорт skipped.
- Impport apply заблокирован до тех пор, пока не существуют `forget_events` + policy detector.
- `ingestion_run_id` тегирует все импортированные строки — можно отменить конкретный импорт-ран.
- Идемпотентность: тот же export file можно применить дважды без дублей (ключи идемпотентности).

## Consequences

### Положительные

- Единый governance-путь: нет "особых" правил для импорта.
- Tombstone применяется и к import — нет воскрешения удалённого контента.
- Идемпотентность: повторный импорт безопасен.
- `ingestion_run_id` позволяет откатить конкретный импорт до применения derived-слоёв.

### Отрицательные / компромиссы

- Import apply заблокирован до Phase 3 (tombstone skeleton) — не реализуется в текущем цикле.
- Synthetic telegram_updates создают дополнительный overhead при импорте больших архивов.
- TODO: архитектор должен определить порядок tombstone-check vs governance detection при
  импорте — что приоритетнее, если одно сообщение попадает под оба условия?
- TODO: что делать с сообщениями в импорте от пользователей, не являющихся членами сообщества
  в момент импорта? Хранить или отклонять?
- TODO: нужен ли re-import после изменения governance-правил? Например, если `#nomem`
  был добавлен к сообщению задним числом.

## Alternatives considered

| Вариант | Почему отклонён |
|---------|-----------------|
| Прямая вставка в chat_messages/message_versions | Обходит governance; tombstone-check требует отдельной реализации; высокий риск ошибки |
| Отдельный import-specific путь нормализации | Дублирование логики; governance может расходиться между путями; поддержка вдвое сложнее |
| Запретить import применение вообще | Теряем ценность исторических данных; ограничивает применимость системы |
| Dry-run как единственный режим | Безопасно, но не даёт поискового и extraction-функционала для истории |

## References

- [HANDOFF.md §1 — invariant 8](../HANDOFF.md): "Import apply must go through same normalization/governance path"
- [HANDOFF.md §2 — phase 2b](../HANDOFF.md): синтетические telegram_updates, idempotent apply
- [HANDOFF.md §9 — idempotency keys](../HANDOFF.md): ключи для synthetic import updates
- [HANDOFF.md §10 — forget_events](../HANDOFF.md): tombstone keys включают export-специфичный ключ
- [ADR-0003](0003-offrecord-irreversibility.md) — governance-правила, которые обязательны при импорте
