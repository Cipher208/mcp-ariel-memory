# mcp-ariel-memory (npm)

Universal Two-Layer Memory MCP Server for AI agents — npm wrapper.

This package installs and runs the Python MCP server. **Requires Python 3.10+** on the system.

## Quick Start

```bash
npx mcp-ariel-memory --transport stdio
```

## Install Globally

```bash
npm install -g mcp-ariel-memory
mcp-ariel-memory --transport http --port 8000
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--transport` | `stdio` (Claude Desktop) or `http` (web clients) | `stdio` |
| `--host` | HTTP host | `0.0.0.0` |
| `--port` | HTTP port | `8000` |
| `--dashboard` | Enable dashboard + metrics | `false` |

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

## Requirements

- Python 3.10+
- pip (usually comes with Python)

## License

MIT
