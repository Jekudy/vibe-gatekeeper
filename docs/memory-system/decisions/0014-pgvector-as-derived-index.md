# ADR-0014: pgvector как derived semantic index; отдельное vector-хранилище отложено

- **Status**: Accepted
- **Date**: 2026-04-27
- **Decision-makers**:
  - @Jekudy — product / architecture owner
  - @<tech-lead-handle> — implementation owner (TODO: заменить когда tech lead появится)
- **Author**: GPT-5.5 Pro / principal architect draft
- **Reviewers**: @<collaborator-handle> (TODO: добавить при онбординге)

## Context

В Phase 4 (hybrid search + q&a) появляется необходимость семантического поиска:
нахождение релевантных сообщений по смыслу, а не только по ключевым словам.
Для этого нужен vector index.

Существует два основных пути:
1. **Отдельное vector-хранилище** (Pinecone, Weaviate, Qdrant, Chroma) — специализированный
   сервис, оптимизированный для vector search.
2. **pgvector** — расширение PostgreSQL, позволяющее хранить векторы прямо в Postgres
   и делать approximate nearest neighbor (ANN) поиск через `ivfflat`/`hnsw` индексы.

При оценке нужно учитывать: мы уже решили, что PostgreSQL — единственный источник истины
(ADR-0001). Векторные эмбеддинги — это derived representation текстового контента, а не
source-of-truth данные. Как и граф (ADR-0005), векторный индекс можно пересобрать из Postgres.

Введение отдельного vector-сервиса создаёт операционную нагрузку:
- дополнительный сервис для мониторинга, backup, обновления
- синхронизация между Postgres и vector store (tombstone должен purge оба!)
- дополнительная точка отказа
- сложнее governance: `#nomem`/`#offrecord` нужно применять в двух местах

## Decision

На Phase 4 используется **pgvector** как Postgres-native derived semantic index.
Отдельное vector-хранилище не вводится в текущем или ближайшем цикле.

Конкретные правила:

1. **pgvector — derived слой.** Векторные эмбеддинги хранятся в Postgres рядом с
   `message_versions`. Колонка `embedding vector(N)` добавляется в Phase 4 как nullable.
2. **Источник истины остаётся Postgres.** Эмбеддинги можно дропнуть и пересобрать.
   Нет эмбеддингов для `#offrecord`/`#nomem`/forgotten контента.
3. **Tombstone purge**: при создании tombstone удаляются эмбеддинги связанных версий.
   Один sweep вместо двух (Postgres + external store).
4. **Governance в одном месте**: `llm_gateway` (ADR-0004) контролирует embedding-вызовы
   так же как extraction-вызовы — через `llm_usage_ledger`.
5. **Отдельный vector-сервис**: разрешён в будущем (Phase 7+), когда:
   - pgvector достигает performance-потолка для нашего объёма
   - появляются требования к cross-modal search (аудио, изображения)
   - операционная зрелость команды позволяет поддерживать дополнительный сервис

## Consequences

### Положительные

- Единое хранилище: tombstone purge затрагивает только Postgres.
- Нет дополнительного сервиса для Phase 4 — меньше infrastructure overhead.
- Транзакционная атомарность: embed + store в одной Postgres-транзакции.
- pgvector достаточно для малых/средних комьюнити (десятки тысяч сообщений).

### Отрицательные / компромиссы

- pgvector медленнее специализированных ANN-движков при большом объёме (>1M векторов).
- Нагрузка на Postgres растёт при large-scale embedding requests.
- Нет metadata-filtering с vector search "из коробки" как в Pinecone/Weaviate
  (требует SQL + vector LIMIT комбинации).
- TODO: определить размерность вектора (1536 для ada-002, 3072 для text-embedding-3-large)
  до Phase 4 — это влияет на индекс и storage.

## Alternatives considered

| Вариант | Почему отклонён |
|---------|-----------------|
| Pinecone / Weaviate / Qdrant как отдельный сервис | Дополнительный сервис; двойная governance; tombstone в двух местах; overengineering для текущего масштаба |
| Только FTS (без векторного поиска) | FTS работает для Phase 4, но семантический поиск нужен для Phase 5 extraction quality |
| ChromaDB embedded | Нарушает ADR-0001 (данные вне Postgres); нет transactional гарантий |
| Откладываем векторный поиск до Phase 7+ | FTS может не дать нужного recall для extraction-кандидатов в Phase 5 |

## References

- [HANDOFF.md §2 — phase 4](../HANDOFF.md): hybrid search + q&a, FTS-first retrieval, evidence bundle
- [HANDOFF.md §2 — phase 10](../HANDOFF.md): graph postponed; аналогичная логика для vector store
- [ADR-0001](0001-postgres-as-source-of-truth.md) — PostgreSQL единственный источник истины
- [ADR-0004](0004-llm-gateway-as-single-boundary.md) — LLM gateway управляет embedding-вызовами тоже
- [ADR-0005](0005-graph-as-projection-not-truth.md) — граф как derived projection (аналогичный принцип)
