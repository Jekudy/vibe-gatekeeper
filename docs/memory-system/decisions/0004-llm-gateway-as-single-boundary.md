# ADR-0004: LLM Gateway — единственная точка входа для LLM

- **Status**: Accepted
- **Date**: 2026-04-27
- **Decision-makers**:
  - @Jekudy — product / architecture owner
  - @<tech-lead-handle> — implementation owner (TODO: заменить когда tech lead появится)
- **Author**: GPT-5.5 Pro / principal architect draft
- **Reviewers**: @<collaborator-handle> (TODO: добавить при онбординге)

## Context

По мере роста системы памяти LLM-вызовы неизбежны: Q&A, extraction, candidates,
саммари, дайджесты. Без центральной точки входа каждый компонент может самостоятельно
вызвать LLM-провайдера, что порождает несколько рисков:

1. **Privacy leak**: компонент может случайно передать в LLM `#offrecord`-контент или
   забытые (tombstone) данные, обойдя governance-фильтры.
2. **Бесконтрольные расходы**: нет budget guard, нет rate limiting, нет audit trail.
3. **Нет единой observability**: невозможно понять суммарный LLM-бюджет или что именно
   было отправлено в модель.
4. **Несогласованные политики**: разные компоненты используют разные промпты, модели,
   температуры — нет единой точки для изменения политики.

В текущем цикле (Phase 0 + Phase 1) LLM-вызовов вообще нет — `llm_gateway` ещё не
существует. Именно поэтому решение принято превентивно: запрет LLM-вызовов вне gateway
действует уже сейчас, а не с момента появления gateway.

## Decision

Все LLM-вызовы в системе проходят через `bot/services/llm_gateway.py` (Phase 5).

- До появления `llm_gateway`: LLM-вызовов нет вообще. Любой код, вызывающий LLM-провайдера
  напрямую, является нарушением и должен быть заблокирован на code review.
- После появления `llm_gateway`: только он вызывает LLM-провайдера; все остальные модули
  используют gateway API.
- Gateway обязан: проверить governance-фильтры (нет `#offrecord`/`#nomem`/forgotten в контексте),
  записать вызов в `llm_usage_ledger`, применить budget guard.
- `llm_usage_ledger` логирует: модель, токены, стоимость, источник вызова, статус.
- Ни один `extraction_run`, ни один Q&A-хэндлер не вызывает LLM-провайдера в обход gateway.

## Consequences

### Положительные

- Единственная точка для enforcement governance-фильтров перед отправкой в LLM.
- Audit trail: все LLM-вызовы логированы в `llm_usage_ledger`.
- Budget guard: можно ввести ограничения не меняя код каждого consumer'а.
- Упрощённая смена провайдера или модели — только в gateway.

### Отрицательные / компромиссы

- Gateway становится single point of failure для всех LLM-фичей — требует высокой надёжности.
- Добавляет слой абстракции: разработчики не могут использовать LLM SDK напрямую.
- TODO: архитектор должен определить: что если governance-check в gateway зависнет или упадёт?
  Должна ли система fail-open или fail-closed для LLM-запросов?

## Alternatives considered

| Вариант | Почему отклонён |
|---------|-----------------|
| Каждый сервис вызывает LLM напрямую | Нет гарантии governance-проверки; нет бюджетного контроля; нет audit trail |
| Middleware/decorator на уровне HTTP | Не охватывает батчинг, streaming, async-вызовы; сложнее протестировать |
| Stateless proxy-сервис | Overengineering для текущего масштаба; deployment overhead |

## References

- [HANDOFF.md §1 — invariant 2](../HANDOFF.md): "No LLM calls outside llm_gateway"
- [HANDOFF.md §7 — service contracts](../HANDOFF.md): `bot/services/governance.py` — fail closed
- [HANDOFF.md §4 — phase 5](../HANDOFF.md): `llm_usage_ledger`, `extraction_runs` в Phase 5
- [HANDOFF.md §16 — risk register](../HANDOFF.md): "LLM cost runaway" риск
- [ADR-0003](0003-offrecord-irreversibility.md) — governance-правила, которые gateway обязан применять
