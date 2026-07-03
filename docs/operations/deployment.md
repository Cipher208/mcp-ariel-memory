# Deployment

## Transports

### stdio

```bash
python -m mcp_server --transport stdio
```

### HTTP (Streamable)

```bash
python -m mcp_server --transport http --port 8000
```

## Docker

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -e ".[all]"
CMD ["python", "-m", "mcp_server", "--transport", "http", "--port", "8000"]
```

## Health Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Status, version, uptime, DB connectivity |
| `GET /ready` | DB + migrations status |
| `GET /alive` | Heartbeat |

## Graceful Shutdown

Handles `SIGTERM` and `SIGINT`:

1. Stops backup cron daemon
2. Stops saga watchdog
3. Closes all database connections
4. Exits cleanly
