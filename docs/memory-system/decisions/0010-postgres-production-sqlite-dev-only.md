# ADR-0010: PostgreSQL — продакшн; SQLite разрешён только в dev/test с dialect-safe репозиториями

- **Status**: Accepted
- **Date**: 2026-04-27
- **Decision-makers**:
  - @Jekudy — product / architecture owner
  - @<tech-lead-handle> — implementation owner (TODO: заменить когда tech lead появится)
- **Author**: GPT-5.5 Pro / principal architect draft
- **Reviewers**: @<collaborator-handle> (TODO: добавить при онбординге)

## Context

ADR-0001 устанавливает PostgreSQL как единственный источник истины. Этот ADR фокусируется
на **runtime scope**: в каких окружениях какой движок допустим, и какие ограничения это
накладывает на код репозиториев.

Существующая проблема (тикет T0-02): `UserRepo.upsert` использовала Postgres-специфичный
`INSERT ... ON CONFLICT DO UPDATE`. В dev и тестах использовался SQLite (через `aiosqlite`),
который не поддерживает эту синтаксию. Результат: тесты падали или давали ложные результаты.

Тем не менее, полный запрет SQLite создаёт проблемы для разработки: запуск Postgres
через docker-compose требует дополнительного шага, замедляет cold start в CI, усложняет
лёгкие unit-тесты.

Компромисс: SQLite **разрешён** в dev/test, но **только** при условии dialect-safe
репозиториев: код репо не должен использовать Postgres-специфичный синтаксис напрямую.

Уточнение: `aiosqlite` остаётся в `dev` зависимостях (`pyproject.toml`) именно для
изолированных in-memory SQLite тестов (`tests/test_scheduler_deadlines.py`).

## Decision

1. **Продакшн**: только PostgreSQL. Staging и CI-тесты с настоящим Postgres обязательны.
2. **Dev/test**: SQLite допустим для изолированных unit/in-memory тестов
   **при условии dialect-safe репозиториев**.
3. **Dialect-safe**: репозитории не используют Postgres-специфичный синтаксис
   (`ON CONFLICT DO UPDATE`, `JSONB`-операторы, `array_agg` и др.) напрямую в SQL-строках.
   Допустимо: SQLAlchemy ORM (нейтральный dialect), либо явная проверка `dialect.name`.
4. **Upsert-паттерн**: для idempotent saves использовать SQLAlchemy `merge()` или
   dialect-safe implementation. Postgres-специфичный `ON CONFLICT` разрешён только
   в миграциях (работают только на Postgres) или в явно помеченных postgres-only методах.
5. **Тесты с реальным Postgres**: все интеграционные тесты для путей, использующих
   Postgres-специфичный синтаксис (migrations, upsert, JSONB) — запускаются только против
   реального Postgres (docker-compose в CI).
6. **`aiosqlite`**: остаётся dev-зависимостью для обратной совместимости с существующими
   тестами (scheduler tests). Новые тесты — только на Postgres.

## Consequences

### Положительные

- Исключает классы багов T0-02: dialect-несовместимость уловлена на этапе разработки.
- Гибкость: простые unit-тесты (бизнес-логика, governance-детектор) работают без Postgres.
- Явная граница: разработчик знает какие паттерны portability требуют, а какие нет.

### Отрицательные / компромиссы

- Dialect-safe ограничение требует дисциплины: легко случайно добавить Postgres-специфику.
- SQLite in-memory не проверяет constraint'ы, которые есть в Postgres (FK, CHECK, UNIQUE partial).
- Требуется docker-compose для полных интеграционных тестов — нет "zero-deps" тест-раннера.

## Alternatives considered

| Вариант | Почему отклонён |
|---------|-----------------|
| Запретить SQLite полностью (только Postgres в тестах) | Overhead для лёгких unit-тестов; замедляет CI cold start |
| Разрешить SQLite везде без dialect-safe ограничения | Повторяет проблему T0-02; silent bugs в продакшне |
| Тестовая база в памяти через Postgres (pg-mem) | Не поддерживает все PG-расширения; ещё один слой абстракции |
| Использовать только SQLAlchemy ORM (нет raw SQL) | ORM не покрывает все случаи; Alembic-миграции всё равно Postgres-only |

## References

- [ADR-0001](0001-postgres-as-source-of-truth.md) — PostgreSQL как единственный источник истины (фундаментальное решение)
- [HANDOFF.md §0 — key risks](../HANDOFF.md): "Dev / prod DB mismatch"
- [HANDOFF.md §5 — ticket T0-02](../HANDOFF.md): Fix / contain sqlite vs postgres upsert
- `pyproject.toml` — `aiosqlite` в `dev` зависимостях с комментарием
