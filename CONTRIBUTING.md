# Contributing to mcp-ariel-memory

Thanks for your interest in contributing!

## Development Setup

```bash
git clone https://github.com/Cipher208/mcp-ariel-memory.git
cd mcp-ariel-memory
pip install -e ".[dev,binary]"
```

## Running Tests

```bash
pytest tests/ -v --timeout=30
```

## Code Style

- Lint: `ruff check .`
- Format: `ruff format .`
- Max line length: 150
- Target: Python 3.10+

## Pull Requests

1. Fork the repo and create a branch from `master`
2. Make your changes
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a PR using the PR template

## Reporting Issues

Use the issue templates for bug reports and feature requests.
