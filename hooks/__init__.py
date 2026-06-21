"""
Hooks Module - 24 hooks (12 user + 12 agent)
"""
from .registry import HookRegistry
from .user_hooks import UserHooks
from .agent_hooks import AgentHooks

__all__ = ["HookRegistry", "UserHooks", "AgentHooks"]
