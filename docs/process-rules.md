# Process Rules

## New Tool Rule
When adding a new MCP tool, always use the corresponding Result class from mcp_server/models.py. Do not return raw dicts.

## Similar Function Rule  
Before merging functions with similar names, verify their algorithms are identical. `_importance_gate` and `_calculate_importance` have different scoring logic despite similar names.

## Platform Flags Rule
Initialize platform-conditional variables at module level before any conditional blocks. Example: `_HAS_AIOSQLITE = False` before `if not _USE_SYNC:`.

## Extracted Data Rule
If you extract data into a variable, consume it. Don't extract `strategy_name` from a table and then use hardcoded values.

## Change Log
When modifying code, update CHANGELOG.md. When modifying architecture, update docs/01-architecture.md.
