"""Shared constants — eliminates string duplication across codebase."""

# Database
DB_NAME = "memory.db"

# Default user
DEFAULT_USER_ID = "default"

# Metric names
METRIC_TOOL_CALLS = "tool_calls"
METRIC_TOOL_REMEMBER = "tool_remember"
METRIC_TOOL_RECALL = "tool_recall"
METRIC_TOOL_FORGET = "tool_forget"
METRIC_TOOL_SESSION_START = "tool_session_start"
METRIC_TOOL_SESSION_END = "tool_session_end"
METRIC_TOOL_EPISODE_SAVE = "tool_episode_save"
METRIC_TOOL_EPISODE_RECALL = "tool_episode_recall"
METRIC_TOOL_GRAPH_ADD = "tool_graph_add"
METRIC_TOOL_GRAPH_QUERY = "tool_graph_query"
METRIC_TOOL_STATS = "tool_stats"
METRIC_TOOL_CONTEXT = "tool_context"
METRIC_TOOL_CONTEXT_INJECT = "tool_context_inject"
METRIC_FTS5_UNAVAILABLE = "rag_fts5_unavailable_total"

# Layers
LAYER_USER = "user"
LAYER_AGENT = "agent"
