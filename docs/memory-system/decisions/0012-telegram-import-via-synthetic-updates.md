# ADR-0012: Telegram Desktop import использует synthetic telegram_updates

- **Status**: Accepted
- **Date**: 2026-04-27
- **Decision-makers**:
  - @Jekudy — product / architecture owner
  - @<tech-lead-handle> — implementation owner (TODO: заменить когда tech lead появится)
- **Author**: GPT-5.5 Pro / principal architect draft
- **Reviewers**: @<collaborator-handle> (TODO: добавить при онбординге)

## Context

ADR-0007 устанавливает принцип: import apply должен проходить через тот же
normalization/governance путь, что и live Telegram-апдейты. Этот ADR описывает
**техническую реализацию** этого принципа — конкретно как import проходит через
единый pipeline.

Проблема без единого пути: если import пишет напрямую в `chat_messages` или
`message_versions`, обходя governance, то:
- `#offrecord`/`#nomem` сообщения воскреснут в базе без policy-проверки
- tombstone-check не сработает — "забытые" сообщения вернутся
- нет `ingestion_run_id` — нельзя откатить конкретный import-ран
- дублирование логики: два разных пути нормализации вместо одного

Решение — создать **synthetic** `telegram_updates` записи для каждого импортируемого
сообщения. Они проходят через тот же pipeline, что и live updates.

## Decision

Telegram Desktop import apply генерирует synthetic `telegram_updates` записи,
которые далее обрабатываются стандартным pipeline.

### Технические детали

1. **Таблица `telegram_updates`** (Phase 1, тикет T1-03) хранит все апдейты:
   и live (`source = 'live'`), и synthetic (`source = 'import'`).

2. **Synthetic update** создаётся для каждого JSON-сообщения из Telegram Desktop export:
   ```
   telegram_updates(
     update_id = NULL,           -- нет реального update_id у импортированных
     source = 'import',
     ingestion_run_id = <run_id>,
     raw_json = <reconstructed telegram-format json>,
     export_message_id = <id из export файла>,
     content_hash = sha256(raw_json)
   )
   ```

3. **Idempotency key** для synthetic updates: `(ingestion_run_id, export_message_id)` —
   повторный import того же файла не создаёт дубли.

4. **Pipeline после synthetic insert** — тот же, что для live:
   - `ingestion.py`: записать raw update → `governance.detect_policy()` (проверить
     `#offrecord`/`#nomem` в том же transaction) → redact при необходимости
   - `normalization.py`: нормализовать в `chat_messages` + `message_versions`
   - tombstone check: перед записью каждого сообщения проверяется `forget_events`
     по ключам `message:<chat_id>:<message_id>`, `message_hash:...`,
     `user:<telegram_user_id>`, `export:<source>:<export_message_id>`
   - при совпадении — import строка skipped, conflict записывается в статистику

5. **Dry-run mode** (Phase 2a): парсер без записи контента, только статистика.
   Dry-run безопасен и разрешён до governance skeleton.

6. **Apply mode** (Phase 2b): заблокирован до появления `forget_events` + policy detector.

7. **Rollback import-рана**: через `ingestion_run_id` — все строки с этим ID можно
   логически скрыть до применения derived слоёв.

## Consequences

### Положительные

- Единый governance путь: нет "особых" правил для import.
- Policy detection (offrecord/nomem) работает для всех источников автоматически.
- Tombstone check работает для import так же как для live.
- Идемпотентность: тот же export file безопасно применить дважды.
- `ingestion_run_id` позволяет audit и rollback конкретного импорта.

### Отрицательные / компромиссы

- Import apply заблокирован до Phase 3 (tombstone skeleton) — в текущем цикле недоступен.
- Synthetic updates создают overhead для больших архивов (тысячи строк в `telegram_updates`).
- `update_id = NULL` требует partial unique index в `telegram_updates`
  (unique где `update_id IS NOT NULL`).
- TODO: что делать с сообщениями от пользователей, не состоявших в сообществе в момент
  импорта? Хранить или отклонять? Требует решения в Phase 2b.

## Alternatives considered

| Вариант | Почему отклонён |
|---------|-----------------|
| Прямая вставка в chat_messages/message_versions | Обходит governance; нет tombstone check; дублирование нормализации; высокий risk |
| Отдельный import-specific нормализатор | Дублирование логики; governance может расходиться; двойная поддержка |
| Пакетный INSERT без governance pipeline | Нет гарантий privacy; resurrection risk; недопустимо |
| Запретить import apply навсегда | Теряем ценность исторического архива |

## References

- [ADR-0007](0007-import-through-same-governance.md) — фундаментальное решение: import через governance путь
- [HANDOFF.md §2 — phase 2b](../HANDOFF.md): synthetic telegram_updates, idempotent apply
- [HANDOFF.md §9 — idempotency keys](../HANDOFF.md): synthetic import idempotency key strategy
- [HANDOFF.md §10 — forget_events](../HANDOFF.md): tombstone keys включают export-специфичный ключ
- [HANDOFF.md §6 — migration T1-03](../HANDOFF.md): `telegram_updates` unique `update_id` (partial where not null)
