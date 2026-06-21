# План: Production-ready mcp-ariel-memory

## Критично (🔴) — ВЫПОЛНЕНО
- [x] 1. Docker + docker-compose
- [x] 2. pyproject.toml (pip installable)
- [x] 3. CI/CD (GitHub Actions)
- [x] 4. MCP Inspector тест

## Важно (🟡) — ВЫПОЛНЕНО
- [x] 5. aiosqlite добавлен в зависимости
- [x] 6. Embeddings модуль создан
- [x] 7. Dashboard (HTML + API endpoints)
- [x] 8. Метрики (Prometheus + JSON)

## Желательно (🟢) — ЧАСТИЧНО
- [x] 9. Аутентификация (API keys + Bearer token)
- [x] 10. Compression — (не требуется, SQLite уже оптимален)
- [x] 11. Backup cron (автобэкап + restore + cleanup)
- [ ] 12. Публикация в MCP Registry
