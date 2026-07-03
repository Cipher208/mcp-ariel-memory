# Quick Start

## Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ariel-memory": {
      "command": "npx",
      "args": ["mcp-ariel-memory", "--transport", "stdio"]
    }
  }
}
```

## Hermes Agent

```yaml
# ~/.hermes/config.yaml
memory:
  provider: ariel-memory
  transport: stdio
```

## HTTP Server

```bash
python -m mcp_server --transport http --port 8000
```

Then configure your MCP client to connect to `http://localhost:8000/mcp`.

## First Memory

Once connected, try:

```
memory_remember: {"layer": "user", "content": "I prefer dark mode", "kind": "preference"}
memory_recall: {"layer": "user", "query": "display preferences"}
```
