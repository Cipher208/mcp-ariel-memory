# ROADMAP

> Планы развития mcp-ariel-memory после v1.0.0.

---

## 1. Публикация и дистрибуция

- [ ] **PyPI публикация** — `twine upload dist/*`, нужен `~/.pypirc` с API токеном
- [ ] **GitHub Release** — создать тег `v1.0.0` + релиз с CHANGELOG
- [ ] **MCP Registry** — обновить описание: "37 tools" → "19 tools"
- [ ] **Docker Hub** — опубликовать образ `ariel-memory`
- [ ] **npm версия** — проверить актуальность `mcp-ariel-memory@1.0.0`, возможно bump

## 2. Архитектура и производительность

- [ ] **Float blobs миграция** — опционально убрать float embeddings (keep_float_blobs=false), оставить только binary
- [ ] **FTS5 улучшения** — добавить триггеры для auto-sync content (сейчас нужен ручной INSERT)
- [ ] **Connection pooling** — SQLite WAL mode + read/write split (read-only replica)
- [ ] **Миграции** — механизм для ALTER TABLE без downtime (сейчас version-based)
- [ ] **Расширенные индексы** — добавить индексы для `temporal_events`, `temporal_links`
- [ ] **Расширить batched reads** — Apply batch processing to all large queries (not just binary search)

## 3. RAG и поиск

- [ ] **Supervised thresholds** — автоматическое обучение на production данных (сейчас вручную)
- [ ] **Hybrid reranker** — добавить cross-encoder reranking после RRF
- [ ] **Embedding cache** — реализовать LRU cache для repeated queries
- [ ] **Auto-strategy** — сделать `auto` стратегию более интеллектуальной (на основе query analytics)
- [ ] **Query expansion** — добавить синонимы и synonyms для FTS5

## 4. Исправления (баги)

- [ ] **Deprecated API cleanup** — удалить `search_rrf()` и `search_binary()` в следующем major version
- [ ] **Tool rename** — `memory_search_rrf` → `memory_search` (после обновления MCP Registry)
- [ ] **CLI improvements** — добавить `--version` флаг, улучшить help сообщения
- [ ] **HTTP transport** — добавить OAuth2/Bearer token для production deployments
- [ ] **Dashboard** — добавить live updates (WebSocket), улучшить UI

## 5. Тестирование и CI

- [ ] **Coverage** — добавить `--cov` в CI, достичь 90% coverage
- [ ] **Load testing** — добавить k6/Artillery тесты для production simulation
- [ ] **Fuzz testing** — добавить fuzz-тесты для парсинга и валидации
- [ ] **Cross-platform testing** — добавить Windows в CI matrix (сейчас только Linux)
- [ ] **Benchmark tracking** — сохранять результаты бенчмарков в CI, отслеживать регрессии

## 6. Документация

- [ ] **API Reference** — автоматическая генерация из docstrings (Sphinx/MkDocs)
- [ ] **Architecture diagrams** — добавить mermaid-диаграммы в docs
- [ ] **Contributing guide** — добавить CONTRIBUTING.md с инструкциями для контрибьюторов
- [ ] **Examples** — добавить примеры использования для Claude Desktop, Hermes, etc.
- [ ] **Migration guide** — добавить руководство по миграции с предыдущих версий

## 7. Безопасность

- [ ] **RBAC** — добавить ролевую модель для multi-tenant deployments
- [ ] **Audit logging** — улучшить формат логов (JSON structured logging)
- [ ] **Rate limiting** — добавить adaptive rate limiting на основе load
- [ ] **Encryption at rest** — добавить AES-256-GCM для database files
- [ ] **Input validation** — добавить валидацию на уровне MCP tools (Pydantic schemas)

## 8. Интеграция

- [ ] **LangChain** — добавить LangChain интеграцию (memory retriever)
- [ ] **AutoGen** — добавить поддержку AutoGen framework
- [ ] **CrewAI** — добавить поддержку CrewAI
- [ ] **LlamaIndex** — добавить LlamaIndex integration
- [ ] **OpenAI plugin** — добавить OpenAI plugin для GPT-4

## 9. Хуки и расширяемость

- [ ] **Plugin system** — реализовать плагины для custom hooks
- [ ] **Webhook support** — добавить webhook callbacks для external services
- [ ] **GraphQL API** — добавить GraphQL endpoint
- [ ] **gRPC support** — добавить gRPC transport (для высокой производительности)
- [ ] **WebSocket** — добавить WebSocket для real-time updates

## 10. Операционные улучшения

- [ ] **Мониторинг** — добавить Prometheus metrics
- [ ] **Alerting** — добавить алерты для critical failures
- [ ] **Health checks** — добавить health check endpoint
- [ ] **Graceful shutdown** — добавить graceful shutdown с drain
- [ ] **Auto-recovery** — добавить автоматическое восстановление после crashes

## 11. Новые фичи

- [ ] **Multi-language support** — добавить поддержку multiple languages (CJK, Arabic)
- [ ] **Voice input** — добавить语音输入 support (via Whisper API)
- [ ] **Image support** — добавить image embedding (CLIP, DALL-E)
- [ ] **Video support** — добавить video embedding (CLIP, VideoMAE)
- [ ] **Code search** — добавить semantic code search (встроить tree-sitter)

## 12. Операционные задачи

- [ ] **Удаление deprecated features** — удалить deprecated wrappers (search_rrf, search_binary)
- [ ] **Cleanup** — удалить неиспользуемые таблицы, индексы, функции
- [ ] **Optimization** — оптимизировать memory usage, CPU, I/O
- [ ] **Scalability** — протестировать на 1M+ записей
- [ ] **Documentation** — обновить все документы для v2.0

---

**Важно:** Этот файл обновляется по мере продвижения. Приоритеты определяются по user feedback и production usage.
