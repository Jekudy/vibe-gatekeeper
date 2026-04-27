# Глоссарий — система памяти Shkoderbot

> Термины, которые встречаются в HANDOFF.md и не очевидны без контекста.
> Каждый термин — 2–3 предложения + ссылка на первоисточник.

*Актуален на 2026-04-27.*

---

## A

### admin review
Процесс ручной проверки администратором сгенерированных кандидатов и knowledge cards перед их активацией.
Карточка не может стать активной без явного одобрения admin'а — это protection от hallucinated extractions.
Реализуется в Phase 6 через admin review UI.
→ [HANDOFF.md §2 Phase 6](HANDOFF.md), [ADR-0006](decisions/0006-summary-as-derived-never-canonical.md)

---

## B

### backfill
Ретроспективное заполнение новой таблицы/колонки данными из существующих строк.
В данном проекте: T1-07 backfill создаёт `message_versions` v1 для всех уже существующих
`chat_messages` на момент миграции. Backfill выполняется чанками, чтобы не блокировать базу.
→ [HANDOFF.md §5 T1-07](HANDOFF.md)

### butler
Будущий action-агент системы (Phase 12), который будет выполнять действия от имени сообщества.
**Не реализуется** в текущих фазах — только design и extension points (permissions, audit boundary, `action_requests`/`action_runs`).
Butler не читает raw DB напрямую; работает исключительно через governance-filtered evidence context.
→ [HANDOFF.md §2 Phase 12](HANDOFF.md), [HANDOFF.md §1 invariant 7](HANDOFF.md)

---

## C

### cascade (tombstone cascade)
Процесс распространения tombstone/forget через все слои данных: `chat_messages` →
`message_versions` → `entities` → `links` → FTS → vectors → candidates → cards → summaries → graph.
Гарантирует, что забытый контент не воскреснет ни в одном downstream-слое.
Реализуется как часть governance (Phase 3, cascade worker skeleton).
→ [HANDOFF.md §10 cascade layers](HANDOFF.md), [ADR-0003](decisions/0003-offrecord-irreversibility.md)

### chat_threads
Таблица тредов (топиков) в группах Telegram с поддержкой тредов (`message_thread_id`).
В текущем цикле: только поле `message_thread_id` на `chat_messages`; полноценная таблица `chat_threads` отложена.
→ [HANDOFF.md §6 migrations](HANDOFF.md)

### citation anchor
Стабильная ссылка на конкретный исторический факт, которая не меняется при редактировании.
В системе роль citation anchor играет `message_version_id` — идентификатор конкретной версии сообщения.
Если сообщение редактируется, старая версия сохраняется, цитата продолжает указывать на неё.
→ [ADR-0002](decisions/0002-message-version-as-citation-anchor.md), [HANDOFF.md §1 invariant 4](HANDOFF.md)

### content_hash (`chv1`)
SHA-256 хэш нормализованного содержимого сообщения, используемый для определения, изменился ли контент.
Формула `chv1`: `[HASH_FORMAT_VERSION, text, caption, message_kind, normalized_entities]` → JSON → SHA-256.
В хэш **не входят** volatile-поля: `date`, `from_user`, `message_id`, `raw_json`.
→ [HANDOFF.md §9 content_hash strategy](HANDOFF.md), [HANDOFF.md §5 T1-08](HANDOFF.md)

---

## D

### derived layers / derived objects
Объекты, сгенерированные из первичных данных и пересобираемые без потери информации:
саммари, дайджесты, кандидаты, граф, FTS-индексы, vectors.
Derived objects не являются источниками истины — при конфликте побеждает Postgres.
→ [ADR-0001](decisions/0001-postgres-as-source-of-truth.md), [ADR-0006](decisions/0006-summary-as-derived-never-canonical.md)

### dry-run (import dry-run)
Режим импорта Telegram Desktop, при котором парсится JSON-экспорт и выводится статистика
(количество сообщений, дубликатов, policy-маркеров) без записи контента в базу.
Dry-run разрешён до полной governance; apply — заблокирован до Phase 3.
→ [HANDOFF.md §2 Phase 2a](HANDOFF.md), [ADR-0007](decisions/0007-import-through-same-governance.md)

---

## E

### evidence bundle
Набор релевантных `message_versions` с `message_version_id`, отобранных FTS/vector-поиском
для ответа на конкретный Q&A-запрос. Q&A-хэндлер отвечает только из evidence bundle, никогда
из "общих знаний" модели. Если evidence нет — хэндлер отказывается отвечать (abstention).
→ [HANDOFF.md §2 Phase 4](HANDOFF.md), [HANDOFF.md §1 invariant 4](HANDOFF.md)

### evidence card
TODO: термин встречается в контексте Phase 4 как концепция "карточки с доказательством".
Уточни у архитектора, является ли это синонимом evidence bundle или отдельной сущностью.

### extraction candidate / memory candidate
Структурированный объект, созданный LLM extraction run из high-signal evidence windows.
Является гипотезой о "факте сообщества" — например, "в чате обсуждалась тема X участником Y".
Кандидат имеет `source_message_version_id` и требует admin review перед переходом в knowledge card.
→ [HANDOFF.md §2 Phase 5](HANDOFF.md), [HANDOFF.md §4 E15](HANDOFF.md)

---

## F

### feature flag
Персистентный флаг в таблице `feature_flags` для включения/отключения функций без деплоя.
Ключи используют dot-notation (`memory.ingestion.raw_updates.enabled`), колонки — underscore (`memory_policy`).
Все memory-флаги по умолчанию OFF; включаются только после прохождения phase gates.
→ [HANDOFF.md §8 feature flag gating](HANDOFF.md), [HANDOFF.md §5 T1-01](HANDOFF.md)

### forget / `/forget`
Telegram-команда для удаления конкретного сообщения из системы памяти.
Автор может забыть своё сообщение; admin — любое; другие участники — нет.
Создаёт tombstone в `forget_events` и запускает cascade. Реализуется в Phase 3.
→ [HANDOFF.md §10 /forget authorization](HANDOFF.md), [HANDOFF.md §5 T3-02](HANDOFF.md)

### forget_events
Таблица tombstone-записей о забытом контенте. Каждая строка — дурабельный факт о том,
что конкретный контент запрещён для использования в системе.
Tombstone не удаляется и не откатывается без явного аудита.
→ [HANDOFF.md §10 forget_events](HANDOFF.md), [ADR-0003](decisions/0003-offrecord-irreversibility.md)

---

## G

### governance
Подсистема управления политиками приватности сообщества: `#nomem`, `#offrecord`, `/forget`,
tombstones, cascade, admin actions. "Governance before memory" — принцип, что ни один
downstream-слой (search, extraction, wiki) не запускается без работающего governance.
→ [HANDOFF.md §10 governance spec](HANDOFF.md), [HANDOFF.md §1 strategy point 3](HANDOFF.md)

---

## H

### hybrid search
Комбинация FTS (full-text search, PostgreSQL `tsvector`) и vector search (pgvector)
для поиска по архиву сообщений. FTS-first: сначала lexical retrieval, затем semantic re-rank.
Результат — evidence bundle с `message_version_id` для Q&A.
→ [HANDOFF.md §2 Phase 4](HANDOFF.md), [HANDOFF.md §4 E10](HANDOFF.md)

---

## I

### idempotency key
Ключ, гарантирующий что повторный вызов операции не создаёт дубликатов. Для live-апдейтов —
`update_id`; для сообщений — `(chat_id, message_id)`; для версий — `(chat_message_id, content_hash)`.
Idempotency обязательна на всех уровнях — это основа безопасного импорта и retry.
→ [HANDOFF.md §9 idempotency keys](HANDOFF.md)

### ingestion_run
Логическая единица пакетного ingestion: live-апдейты или одна import-сессия.
Каждая строка в `telegram_updates` тегируется `ingestion_run_id`.
Позволяет откатить конкретный import-ран до применения derived-слоёв.
→ [HANDOFF.md §5 T1-02](HANDOFF.md), [HANDOFF.md §7 ingestion.py](HANDOFF.md)

---

## K

### knowledge card
Утверждённая структурированная запись знания сообщества: факт, решение, экспертиза участника.
Card активируется только после admin review и наличия `card_sources` → `message_version_id`.
Является единицей community memory, на которую ссылаются wiki, digest, граф.
→ [HANDOFF.md §2 Phase 6](HANDOFF.md), [ADR-0006](decisions/0006-summary-as-derived-never-canonical.md)

---

## L

### llm_gateway
Единственная точка входа для всех LLM-вызовов в системе.
Проверяет governance-фильтры, логирует в `llm_usage_ledger`, применяет budget guard.
До Phase 5: LLM-вызовов нет совсем. Нарушение этого правила — критический баг.
→ [ADR-0004](decisions/0004-llm-gateway-as-single-boundary.md), [HANDOFF.md §1 invariant 2](HANDOFF.md)

---

## M

### message_kind
Классификация типа сообщения: `text`, `photo`, `video`, `document`, `sticker`, `audio`,
`voice`, `unknown_prior_version`, и др. Хранится в `chat_messages.message_kind`.
Входит в `content_hash` (рецепт `chv1`) для корректной дедупликации.
→ [HANDOFF.md §5 T1-11](HANDOFF.md), [HANDOFF.md §9 content_hash](HANDOFF.md)

### memory_policy
Колонка на `chat_messages`, отражающая governance-статус сообщения: `normal`, `nomem`, `offrecord`.
Устанавливается детектором `detect_policy()` в момент ingestion (не постфактум).
Определяет, может ли сообщение участвовать в search / extraction / digest / wiki / LLM.
→ [HANDOFF.md §10 policy table](HANDOFF.md), [HANDOFF.md §5 T1-12](HANDOFF.md)

### message_version
Конкретная версия содержимого сообщения, зафиксированная append-only в `message_versions`.
v1 создаётся при первом сохранении; v2 — при изменении `content_hash` (редактирование).
Является citation anchor: цитаты в Q&A, cards, summaries указывают на `message_version_id`.
→ [ADR-0002](decisions/0002-message-version-as-citation-anchor.md), [HANDOFF.md §5 T1-06](HANDOFF.md)

---

## N

### `#nomem`
Тег в тексте/caption сообщения: "не включать в систему памяти".
Сообщение с `#nomem` сохраняется в `chat_messages` (raw может остаться), но исключается
из всех derived-слоёв: FTS, vector, extraction, Q&A, digest, wiki, граф, LLM.
→ [HANDOFF.md §10 #nomem](HANDOFF.md), [ADR-0003](decisions/0003-offrecord-irreversibility.md)

### normalization
Процесс преобразования raw Telegram-апдейта в структурированные строки базы данных.
Выполняется `bot/services/normalization.py`: `chat_messages`, `message_versions`,
`entities`, `links`, `attachments`. Нормализация происходит после governance-проверки.
→ [HANDOFF.md §7 normalization.py](HANDOFF.md), [HANDOFF.md §9 live message update flow](HANDOFF.md)

---

## O

### `#offrecord`
Тег в тексте/caption: "это сообщение конфиденциально и не должно храниться в видимом виде".
В отличие от `#nomem`, для `#offrecord` выполняется редакция: `text`/`caption`/`entities`
удаляются из `raw_json` в той же транзакции, что и сохранение. Хранятся только метаданные.
→ [ADR-0003](decisions/0003-offrecord-irreversibility.md), [AUTHORIZED_SCOPE.md](AUTHORIZED_SCOPE.md)

### offrecord_marks
Audit-таблица, фиксирующая каждый случай обнаружения `#offrecord` или `#nomem`.
Создаётся в той же транзакции, что и редакция `raw_json`. Используется для audit trail
и не может быть удалена без явного tombstone-процесса.
→ [HANDOFF.md §5 T1-13](HANDOFF.md), [ADR-0003](decisions/0003-offrecord-irreversibility.md)

---

## P

### phase gate
Набор критериев, которые должны быть выполнены перед переходом к следующей фазе разработки.
Предотвращает "прыжки вперёд": нельзя строить extraction без governance, wiki без review.
Примеры gate-критериев: "tombstone + policy detection существуют" → разрешён import apply.
→ [HANDOFF.md §1 phase gates table](HANDOFF.md), [ROADMAP.md](ROADMAP.md)

---

## R

### raw archive / `telegram_updates`
Таблица с полными raw JSON-апдейтами от Telegram, сохранёнными до нормализации.
Каждая строка идемпотентна по `update_id`. Является audit trail и источником для rebuild
нормализованных данных при необходимости. Для `#offrecord` — контент редактируется до commit'а.
→ [HANDOFF.md §5 T1-03](HANDOFF.md), [HANDOFF.md §9 live message flow](HANDOFF.md)

---

## S

### source of truth
Единственный авторитетный источник данных, которому доверяют при конфликтах.
В данной системе: PostgreSQL (для всего); `message_versions` (для цитат внутри Postgres).
Граф, саммари, дайджесты — не источники истины, а derived projections.
→ [ADR-0001](decisions/0001-postgres-as-source-of-truth.md), [HANDOFF.md §1 invariant 5,6](HANDOFF.md)

### summary (саммари)
LLM-генерированная выжимка активности за период (daily summary Phase 7, weekly digest Phase 8).
Саммари всегда derived: каждый bullet должен иметь ссылку на `message_version_id`.
При tombstone источника — соответствующий bullet redacted или удалён.
→ [ADR-0006](decisions/0006-summary-as-derived-never-canonical.md), [HANDOFF.md §2 Phase 7](HANDOFF.md)

### synthetic `telegram_update`
Искусственная строка в `telegram_updates`, созданная import-процессом вместо реального Telegram-апдейта.
Позволяет импорту использовать тот же `ingestion → governance → normalization` путь.
Тегируется `ingestion_run_id` для отслеживания и возможного rollback.
→ [ADR-0007](decisions/0007-import-through-same-governance.md), [HANDOFF.md §2 Phase 2b](HANDOFF.md)

---

## T

### tombstone
Дурабельная запись о том, что конкретный контент запрещён в системе навсегда (или до явной отмены через аудит).
Хранится в `forget_events`. Не удаляется casually. Проверяется при импорте, rebuild, cascade.
Ключи: `message:<chat_id>:<message_id>`, `message_hash:<sha256>`, `user:<telegram_user_id>`.
→ [HANDOFF.md §10 forget_events](HANDOFF.md), [ADR-0003](decisions/0003-offrecord-irreversibility.md), [HANDOFF.md §1 invariant 9](HANDOFF.md)

---

## V

### visibility filter
Механизм контроля доступа к данным: определяет, что видит member vs internal vs public.
Применяется в wiki, catalog, expertise pages. Public wiki отключён по умолчанию до
прохождения governance + review gates.
→ [HANDOFF.md §2 Phase 9](HANDOFF.md), [HANDOFF.md §1 invariant 10](HANDOFF.md)
