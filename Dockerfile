FROM python:3.12-slim

WORKDIR /app

# Copy everything needed for metadata
COPY pyproject.toml README.md README_EN.md LICENSE ./

# Install dependencies
RUN pip install --no-cache-dir .

# Copy the rest of the code
COPY . .

RUN mkdir -p /data

# Run as non-root user for security
RUN useradd -m -u 1000 ariel && chown -R ariel:ariel /app /data
USER ariel

ENV MCP_MEMORY_DATA_DIR=/data
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Mount config.yaml as volume at runtime:
# docker run -v $(pwd)/config.yaml:/app/config.yaml -p 8000:8000 ariel-memory
# Or use docker-compose (see docker-compose.yml)

ENTRYPOINT ["python", "-m", "mcp_server"]
CMD ["--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
