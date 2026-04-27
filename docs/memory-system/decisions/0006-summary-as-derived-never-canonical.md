# ADR-0006: Саммари — производное, никогда не каноническое

- **Status**: Accepted
- **Date**: 2026-04-27
- **Decision-makers**: TODO — уточни у архитектора

## Context

Система производит различные derived-объекты: daily summaries (Phase 7), weekly digests
(Phase 8), knowledge cards (Phase 6), observations (Phase 5). Возникает соблазн
использовать эти объекты как входные данные для следующих LLM-шагов — "summary of summaries"
или "card based on digest excerpt".

Проблема: если LLM-генерированное саммари используется как источник истины, цепочка
деградирует по нескольким причинам:
1. **Hallucination propagation**: ошибка на любом шаге цепи усиливается в следующем.
2. **Governance bypass**: саммари может содержать перефразированный `#offrecord`-контент
   без явной ссылки на источник — невозможно применить forget/tombstone к такому "производному факту".
3. **Неверифицируемые цитаты**: нельзя проверить, откуда взялось утверждение в саммари,
   если источник — другое саммари.

## Decision

Саммари, дайджесты, observations, candidates никогда не являются каноническими источниками.

- Каждое утверждение в derived-объекте должно иметь ссылку на `message_version_id`
  или approved knowledge card (которая в свою очередь имеет `card_sources` → `message_version_id`).
- LLM-extraction и LLM-generation работают только с evidence, построенным из
  message_versions + governance-filtered FTS (Phase 4+).
- Derived-объекты перестраиваемые: их можно дропнуть и сгенерировать заново из первичных источников.
- При tombstone/forget: если источник-версия вошла в саммари — соответствующий bullet
  в саммари должен быть redacted или удалён (cascade в Phase 3+).
- Knowledge cards (Phase 6) становятся approved только после admin review с проверкой `card_sources`.
- Без `card_sources` карточка не может стать активной.

## Consequences

### Положительные

- Цепочка источников всегда верифицируема: card → message_version → raw event.
- Forget/tombstone можно применить к derived-объектам через cascade по `source_id`.
- Нет hallucination amplification через "summary of summaries".
- Упрощён audit: каждое утверждение системы имеет первоисточник.

### Отрицательные / компромиссы

- Генерация derived-объектов сложнее: нельзя просто "попросить LLM написать саммари на основе вчерашнего".
- Требует явного хранения `summary_sources` и `card_sources` — дополнительные таблицы и JOIN'ы.
- TODO: архитектор должен прояснить, что происходит с уже опубликованным саммари,
  если один из его источников-сообщений получает tombstone после публикации.
  Автоматический retract? Флаг "требует ревью"? Немедленная редакция?

## Alternatives considered

| Вариант | Почему отклонён |
|---------|-----------------|
| Использовать саммари как промежуточный контекст для LLM | Hallucination propagation; governance leak через перефразирование |
| Хранить карточки без card_sources | Нет возможности применить forget; нет verifiable audit trail |
| LLM сам решает, что цитировать | Нет гарантии, что все цитаты укажут на реальные message_version_id |

## References

- [HANDOFF.md §1 — invariant 5](../HANDOFF.md): "Summary is never canonical truth"
- [HANDOFF.md §2 — phase 6](../HANDOFF.md): "card cannot become active without source"
- [HANDOFF.md §2 — phase 7](../HANDOFF.md): "every bullet has source; forgotten source redacts bullet"
- [ADR-0002](0002-message-version-as-citation-anchor.md) — message_version как якорь
- [ADR-0003](0003-offrecord-irreversibility.md) — cascade tombstone на derived-объекты
