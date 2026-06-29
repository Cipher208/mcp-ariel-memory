# Hooks — hooks/ (integrated into tool pipeline)

24 hooks, actively called from mcp_server/ on every tool call.

## HookRegistry (hooks/registry.py)

Central dispatch for all hooks. Manages registration and execution of hook handlers.

### Class: `HookRegistry`

```python
class HookRegistry:
    def __init__(self)
```

**Description**: Creates a new hook registry instance with an empty hook map.

**Attributes**:
- `_hooks: Dict[str, List[Callable]]` — Internal mapping of hook names to handler lists.

---

### `HookRegistry.register(hook_name: str, handler: Callable) -> None`

**Description**: Register a handler function for a specific hook name. Multiple handlers can be registered for the same hook.

**Parameters**:
- `hook_name` (str): The name of the hook to register the handler for.
- `handler` (Callable): A callable that accepts a context dict and returns a result dict.

**Returns**: None

**Example**:
```python
from hooks.registry import HookRegistry

registry = HookRegistry()

def my_handler(ctx):
    return {"action": "processed", "input": ctx.get("text", "")}

registry.register("message_received", my_handler)
```

---

### `HookRegistry.fire(hook_name: str, layer: str, context: Dict[str, Any]) -> Dict[str, Any]`

**Description**: Fire a hook by name, executing all registered handlers. Checks if the hook is enabled in config before executing. Known hooks are validated against predefined lists for user and agent layers.

**Parameters**:
- `hook_name` (str): The name of the hook to fire.
- `layer` (str): The layer context ("user" or "agent") for config lookup.
- `context` (Dict[str, Any]): Context data passed to all handlers.

**Returns**:
- `Dict[str, Any]`: 
  - `{"skipped": True, "reason": "hook_disabled"}` — if hook is disabled in config
  - `{"skipped": True, "reason": "no_handlers"}` — if no handlers registered
  - `{"results": [...], "handler_count": int}` — results from all handlers

**Known User Hooks**: `message_received`, `message_sent`, `state_delta`, `consolidation`, `emotion_trigger`, `nightly`, `importance_gate`, `auto_context`, `forgetting_ritual`, `retrieval_router`, `conflict_resolver`, `dream_buffer`

**Known Agent Hooks**: `error_occurred`, `decision_made`, `self_correction`, `personality_shift`, `emotion_context`, `wiki_agent`, `consolidation`, `forgetting_ritual`, `auto_context`, `retrieval_router`, `conflict_resolver`, `emotion`

**Example**:
```python
from hooks.registry import hook_registry

result = hook_registry.fire("message_received", "user", {"text": "Hello world"})
print(result)
# {"results": [{"action": "store_to_l1", "importance": 0.5, "text": "Hello wo..."}], "handler_count": 1}
```

---

### `HookRegistry.list_hooks() -> Dict[str, int]`

**Description**: List all registered hooks and their handler counts.

**Parameters**: None

**Returns**: `Dict[str, int]` — mapping of hook names to number of registered handlers.

**Example**:
```python
from hooks.registry import hook_registry

hooks = hook_registry.list_hooks()
print(hooks)
# {"message_received": 1, "error_occurred": 1, ...}
```

---

## UserHooks (hooks/user_hooks.py)

12 hooks for user memory events. Automatically registers all handlers on initialization.

### Class: `UserHooks`

```python
class UserHooks:
    def __init__(self, user_id: str = "default")
```

**Description**: Creates a UserHooks instance and registers all 12 user hooks with the global hook_registry.

**Parameters**:
- `user_id` (str, optional): The user ID for memory operations. Defaults to `"default"`.

**Attributes**:
- `user_id` (str): The user ID.
- `emotion_trigger` (EmotionTrigger): Emotion detection instance.

---

### `UserHooks._message_received(ctx: Dict[str, Any]) -> Dict[str, Any]`

**Description**: Hook handler for incoming messages. Calculates importance score and stores to L1 buffer.

**Parameters**:
- `ctx` (Dict[str, Any]): Context dict with key `"text"` containing the message.

**Returns**: `Dict[str, Any]` — `{"action": "store_to_l1", "importance": float, "text": str}`

**Example**:
```python
from hooks.user_hooks import UserHooks

uh = UserHooks("alice")
result = uh._message_received({"text": "How do I configure Redis?"})
print(result)
# {"action": "store_to_l1", "importance": 0.8, "text": "How do I configure Redis?"}
```

---

### `UserHooks._message_sent(ctx: Dict[str, Any]) -> Dict[str, Any]`

**Description**: Hook handler for outgoing agent messages. Stores assistant reply to L1 buffer.

**Parameters**:
- `ctx` (Dict[str, Any]): Context dict with key `"text"` containing the message.

**Returns**: `Dict[str, Any]` — `{"action": "store_to_l1", "role": "assistant", "text": str}`

**Example**:
```python
result = uh._message_sent({"text": "Redis can be configured via redis.conf"})
# {"action": "store_to_l1", "role": "assistant", "text": "Redis can be configured via redis.conf"}
```

---

### `UserHooks._state_delta(ctx: Dict[str, Any]) -> Dict[str, Any]`

**Description**: Hook handler for state changes. Creates an episode in L3 if delta is non-empty.

**Parameters**:
- `ctx` (Dict[str, Any]): Context dict with key `"delta"` containing the state changes.

**Returns**: `Dict[str, Any]` — `{"action": "save_episode", "summary": str, "weight": 0.4}` or `{"action": "skip"}`

**Example**:
```python
result = uh._state_delta({"delta": {"mood": "happy", "focus": "coding"}})
# {"action": "save_episode", "summary": "State changed: ['mood', 'focus']", "weight": 0.4}
```

---

### `UserHooks._consolidation(ctx: Dict[str, Any]) -> Dict[str, Any]`

**Description**: Hook handler for memory consolidation. Moves items from L1 to L2/L3 using ConsolidationEngine.

**Parameters**:
- `ctx` (Dict[str, Any]): Context dict with key `"staging_items"` containing items to consolidate.

**Returns**: `Dict[str, Any]` — `{"action": "consolidated", ...}` with consolidation results.

**Example**:
```python
result = uh._consolidation({"staging_items": [{"text": "Important fact", "importance": 0.7}]})
# {"action": "consolidated", "consolidated": 1, "promoted": 0}
```

---

### `UserHooks._emotion_trigger(ctx: Dict[str, Any]) -> Dict[str, Any]`

**Description**: Hook handler for emotional content detection. Saves emotional episodes to L3.

**Parameters**:
- `ctx` (Dict[str, Any]): Context dict with key `"text"` containing the message.

**Returns**: `Dict[str, Any]` — `{"action": "save_episode", "reason": str, "weight": float}` or `{"action": "skip"}`

**Example**:
```python
result = uh._emotion_trigger({"text": "I'm so frustrated with this bug!"})
# {"action": "save_episode", "reason": "frustration_detected", "weight": 0.8}
```

---

### `UserHooks._nightly(ctx: Dict[str, Any]) -> Dict[str, Any]`

**Description**: Hook handler for nightly cron job. Creates a diary entry with daily summary.

**Parameters**:
- `ctx` (Dict[str, Any]): Context dict with key `"daily_summary"`.

**Returns**: `Dict[str, Any]` — `{"action": "create_diary", "summary": str}`

**Example**:
```python
result = uh._nightly({"daily_summary": "Discussed Redis configuration and debugging tips"})
# {"action": "create_diary", "summary": "Discussed Redis configuration and debugging tips"}
```

---

### `UserHooks._importance_gate(ctx: Dict[str, Any]) -> Dict[str, Any]`

**Description**: Hook handler for noise filtering. Calculates importance score and decides whether to bypass storage.

**Parameters**:
- `ctx` (Dict[str, Any]): Context dict with key `"text"` containing the message.

**Returns**: `Dict[str, Any]` — `{"importance": float, "bypass": bool}` — bypass is True if score < 0.3.

**Example**:
```python
result = uh._importance_gate({"text": "How do I configure Redis?"})
# {"importance": 0.8, "bypass": False}

result = uh._importance_gate({"text": "ok"})
# {"importance": 0.3, "bypass": True}
```

---

### `UserHooks._auto_context(ctx: Dict[str, Any]) -> Dict[str, Any]`

**Description**: Hook handler for automatic context injection. Routes query through RetrievalRouter.

**Parameters**:
- `ctx` (Dict[str, Any]): Context dict with key `"query"`.

**Returns**: `Dict[str, Any]` — `{"context": List, "strategy": str}`

**Example**:
```python
result = uh._auto_context({"query": "How to use Redis?"})
# {"context": ["Redis is...", "Key commands..."], "strategy": "semantic"}
```

---

### `UserHooks._forgetting_ritual(ctx: Dict[str, Any]) -> Dict[str, Any]`

**Description**: Hook handler for periodic memory cleanup. Executes forgetting system cleanup.

**Parameters**:
- `ctx` (Dict[str, Any]): Context dict (unused).

**Returns**: `Dict[str, Any]` — cleanup results from ForgettingSystem.

**Example**:
```python
result = uh._forgetting_ritual({})
# {"cleaned": 15, "archived": 3}
```

---

### `UserHooks._retrieval_router(ctx: Dict[str, Any]) -> Dict[str, Any]`

**Description**: Hook handler for retrieval strategy routing. Returns routing metadata.

**Parameters**:
- `ctx` (Dict[str, Any]): Context dict with key `"query"`.

**Returns**: `Dict[str, Any]` — `{"strategy": str, "confidence": float, "count": int}`

**Example**:
```python
result = uh._retrieval_router({"query": "Redis configuration"})
# {"strategy": "semantic", "confidence": 0.85, "count": 5}
```

---

### `UserHooks._conflict_resolver(ctx: Dict[str, Any]) -> Dict[str, Any]`

**Description**: Hook handler for memory conflict resolution. Checks for conflicting memories.

**Parameters**:
- `ctx` (Dict[str, Any]): Context dict with key `"content"`.

**Returns**: `Dict[str, Any]` — conflict check results.

**Example**:
```python
result = uh._conflict_resolver({"content": "Redis default port is 6379"})
# {"conflicts": [], "resolved": True}
```

---

### `UserHooks._dream_buffer(ctx: Dict[str, Any]) -> Dict[str, Any]`

**Description**: Hook handler for dream buffer staging. Adds content to staging for later processing.

**Parameters**:
- `ctx` (Dict[str, Any]): Context dict with key `"text"`.

**Returns**: `Dict[str, Any]` — `{"action": "add_to_staging", "content": str}`

**Example**:
```python
result = uh._dream_buffer({"text": "Interesting pattern noticed..."})
# {"action": "add_to_staging", "content": "Interesting pattern noticed..."}
```

---

### `UserHooks._calculate_importance(text: str) -> float`

**Description**: Calculate importance score for a message based on heuristics.

**Parameters**:
- `text` (str): The message text.

**Returns**: `float` — importance score between 0.0 and 1.0.

**Scoring heuristics**:
- Base score: 0.3
- Length > 15 chars: +0.2
- Length > 100 chars: +0.1
- Contains "?": +0.2
- Lines > 2: +0.1

**Example**:
```python
score = uh._calculate_importance("How do I configure Redis in production?")
# 0.8 (base 0.3 + length 0.2 + question 0.2 + ...)

score = uh._calculate_importance("ok")
# 0.3
```

---

## AgentHooks (hooks/agent_hooks.py)

12 hooks for agent identity events. Automatically registers all handlers on initialization.

### Class: `AgentHooks`

```python
class AgentHooks:
    def __init__(self, user_id: str = "default")
```

**Description**: Creates an AgentHooks instance and registers all 12 agent hooks with the global hook_registry.

**Parameters**:
- `user_id` (str, optional): The user ID for memory operations. Defaults to `"default"`.

**Attributes**:
- `user_id` (str): The user ID.
- `graph` (EpistemicGraph): Epistemic graph instance for agent layer.

---

### `AgentHooks._error_occurred(ctx: Dict[str, Any]) -> Dict[str, Any]`

**Description**: Hook handler for error events. Logs error to epistemic graph for pattern analysis.

**Parameters**:
- `ctx` (Dict[str, Any]): Context dict with key `"error"` containing the error message.

**Returns**: `Dict[str, Any]` — `{"action": "error_analyzed", "node_id": int}`

**Example**:
```python
from hooks.agent_hooks import AgentHooks

ah = AgentHooks("alice")
result = ah._error_occurred({"error": "NullPointerException at line 42"})
# {"action": "error_analyzed", "node_id": 5}
```

---

### `AgentHooks._decision_made(ctx: Dict[str, Any]) -> Dict[str, Any]`

**Description**: Hook handler for decision events. Logs decision and rationale to epistemic graph.

**Parameters**:
- `ctx` (Dict[str, Any]): Context dict with keys `"decision"` and `"rationale"`.

**Returns**: `Dict[str, Any]` — `{"action": "decision_logged", "node_id": int}`

**Example**:
```python
result = ah._decision_made({
    "decision": "Use Redis for caching",
    "rationale": "Better performance than memcached for this use case"
})
# {"action": "decision_logged", "node_id": 6}
```

---

### `AgentHooks._self_correction(ctx: Dict[str, Any]) -> Dict[str, Any]`

**Description**: Hook handler for self-correction events. Logs error-fix pairs to epistemic graph.

**Parameters**:
- `ctx` (Dict[str, Any]): Context dict with keys `"error"` and `"fix"`.

**Returns**: `Dict[str, Any]` — `{"action": "correction_logged", "node_id": int}`

**Example**:
```python
result = ah._self_correction({
    "error": "Wrong Redis command syntax",
    "fix": "Use SET instead of PUT"
})
# {"action": "correction_logged", "node_id": 7}
```

---

### `AgentHooks._personality_shift(ctx: Dict[str, Any]) -> Dict[str, Any]`

**Description**: Hook handler for personality evolution events. Logs trait changes to epistemic graph.

**Parameters**:
- `ctx` (Dict[str, Any]): Context dict with key `"shift"` describing the personality change.

**Returns**: `Dict[str, Any]` — `{"action": "personality_evolved", "node_id": int}`

**Example**:
```python
result = ah._personality_shift({"shift": "Became more patient with beginners"})
# {"action": "personality_evolved", "node_id": 8}
```

---

### `AgentHooks._emotion_context(ctx: Dict[str, Any]) -> Dict[str, Any]`

**Description**: Hook handler for emotional context events. Logs emotion-in-context to epistemic graph.

**Parameters**:
- `ctx` (Dict[str, Any]): Context dict with keys `"emotion"` and `"context"`.

**Returns**: `Dict[str, Any]` — `{"action": "emotion_logged", "node_id": int}`

**Example**:
```python
result = ah._emotion_context({
    "emotion": "excitement",
    "context": "solving a complex algorithm"
})
# {"action": "emotion_logged", "node_id": 9}
```

---

### `AgentHooks._wiki_agent(ctx: Dict[str, Any]) -> Dict[str, Any]`

**Description**: Hook handler for wiki sync events. Triggers wiki synchronization.

**Parameters**:
- `ctx` (Dict[str, Any]): Context dict with key `"summary"`.

**Returns**: `Dict[str, Any]` — `{"action": "wiki_sync", "summary": str}`

**Example**:
```python
result = ah._wiki_agent({"summary": "Updated Redis documentation"})
# {"action": "wiki_sync", "summary": "Updated Redis documentation"}
```

---

### `AgentHooks._consolidation(ctx: Dict[str, Any]) -> Dict[str, Any]`

**Description**: Hook handler for agent memory consolidation. Consolidates staging items with higher importance threshold.

**Parameters**:
- `ctx` (Dict[str, Any]): Context dict with key `"staging_items"`.

**Returns**: `Dict[str, Any]` — `{"action": "agent_consolidated", ...}` with consolidation results.

**Example**:
```python
result = ah._consolidation({"staging_items": [{"text": "Important insight", "importance": 0.8}]})
# {"action": "agent_consolidated", "consolidated": 1}
```

---

### `AgentHooks._forgetting_ritual(ctx: Dict[str, Any]) -> Dict[str, Any]`

**Description**: Hook handler for agent memory cleanup. Executes forgetting system cleanup.

**Parameters**:
- `ctx` (Dict[str, Any]): Context dict (unused).

**Returns**: `Dict[str, Any]` — cleanup results from ForgettingSystem.

**Example**:
```python
result = ah._forgetting_ritual({})
# {"cleaned": 10, "archived": 2}
```

---

### `AgentHooks._auto_context(ctx: Dict[str, Any]) -> Dict[str, Any]`

**Description**: Hook handler for agent context injection. Routes query through agent-layer RetrievalRouter.

**Parameters**:
- `ctx` (Dict[str, Any]): Context dict with key `"query"`.

**Returns**: `Dict[str, Any]` — `{"context": List, "strategy": str}`

**Example**:
```python
result = ah._auto_context({"query": "Previous debugging approaches"})
# {"context": ["Used binary search...", "Checked logs..."], "strategy": "semantic"}
```

---

### `AgentHooks._retrieval_router(ctx: Dict[str, Any]) -> Dict[str, Any]`

**Description**: Hook handler for agent retrieval routing. Returns routing metadata for agent layer.

**Parameters**:
- `ctx` (Dict[str, Any]): Context dict with key `"query"`.

**Returns**: `Dict[str, Any]` — `{"strategy": str, "confidence": float}`

**Example**:
```python
result = ah._retrieval_router({"query": "Error patterns"})
# {"strategy": "graph", "confidence": 0.9}
```

---

### `AgentHooks._conflict_resolver(ctx: Dict[str, Any]) -> Dict[str, Any]`

**Description**: Hook handler for agent memory conflict resolution.

**Parameters**:
- `ctx` (Dict[str, Any]): Context dict with key `"content"`.

**Returns**: `Dict[str, Any]` — conflict check results.

**Example**:
```python
result = ah._conflict_resolver({"content": "Best practice: use connection pooling"})
# {"conflicts": [], "resolved": True}
```

---

### `AgentHooks._emotion(ctx: Dict[str, Any]) -> Dict[str, Any]`

**Description**: Hook handler for agent emotion recording. Logs emotion to epistemic graph.

**Parameters**:
- `ctx` (Dict[str, Any]): Context dict with key `"emotion"`.

**Returns**: `Dict[str, Any]` — `{"action": "emotion_recorded", "node_id": int}`

**Example**:
```python
result = ah._emotion({"emotion": "satisfaction"})
# {"action": "emotion_recorded", "node_id": 10}
```

---

## Integration in mcp_server

### memory_remember (layer="user") — calls 2 hooks:

```python
# 1. importance_gate — noise filter
gate = app.user_hooks._importance_gate({"text": value})
if gate.get("bypass"):
    return {"status": "skipped", "reason": "below_importance_threshold"}

# 2. emotion_trigger — emotional analysis (RU + EN + emoji)
should_save, reason, weight = app.emotion_trigger.should_save(value)
if should_save:
    await app.mm.user_memory(user_id).l3.save(...)
```

### memory_remember (layer="agent") — automatically logs to graph:

```python
if "error" in key:
    app.agent_graph.add_node(..., "error_analysis", ["error_pattern"])
elif "decision" in key:
    app.agent_graph.add_node(..., "decision_log", ["decided_because"])
```

---

## Configuration (config.yaml)

**Enable/disable hooks:**

```yaml
hooks:
  user:
    message_received: true
    message_sent: true
    state_delta: true
    consolidation: true
    emotion_trigger: false  # disable
    nightly: true
    importance_gate: true
    auto_context: true
    forgetting_ritual: true
    retrieval_router: true
    conflict_resolver: true
    dream_buffer: true
  agent:
    error_occurred: true
    decision_made: true
    self_correction: true
    personality_shift: true
    emotion_context: true
    wiki_agent: true
    consolidation: true
    forgetting_ritual: true
    auto_context: true
    retrieval_router: true
    conflict_resolver: true
    emotion: true
```
