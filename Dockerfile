FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

RUN mkdir -p /data

ENV MCP_MEMORY_DATA_DIR=/data
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# config.yaml монтируется как volume при запуске:
# docker run -v $(pwd)/config.yaml:/app/config.yaml -p 8000:8000 ariel-memory
# Или через docker-compose (см. docker-compose.yml)

ENTRYPOINT ["python", "-m", "mcp_ariel_memory"]
CMD ["--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
