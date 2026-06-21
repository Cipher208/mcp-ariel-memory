"""
Core Memory Module - L1-L4
Two-layer: user facts + agent identity
"""
from pathlib import Path
from typing import Optional, List, Dict
from .reflex import ReflexBuffer
from .session import SessionStore
from .episodic import EpisodicMemory
from .memory import CoreMemory
from config import config

class MemoryLayer:
    """Unified memory layer for both user and agent."""
    
    def __init__(self, layer_type: str, user_id: str = "default"):
        self.layer_type = layer_type  # "user" or "agent"
        self.user_id = user_id
        self.l1 = ReflexBuffer(max_size=config.get_limit("l1_buffer_size"))
        self.l2 = SessionStore()
        self.l3 = EpisodicMemory()
        self.l4 = CoreMemory()
    
    def remember(self, key: str, value: str, importance: float = 0.5) -> str:
        """Save to L4 (CoreMemory)."""
        return self.l4.save(self.user_id, key, value, importance)
    
    def recall(self, query: str, limit: int = 10) -> List[Dict]:
        """Search across L1-L4."""
        results = []
        results.extend(self.l4.search(self.user_id, query, limit))
        results.extend(self.l3.search(self.user_id, query, limit))
        return results[:limit]
    
    def forget(self, key: str) -> bool:
        """Delete from L4."""
        return self.l4.delete(self.user_id, key)
    
    def get_context(self) -> str:
        """Get full context for prompt injection."""
        parts = []
        
        # L1: Recent messages
        recent = self.l1.get_recent(5)
        if recent:
            parts.append("RECENT: " + "; ".join([r.content[:50] for r in recent]))
        
        # L4: Key facts
        facts = self.l4.get_all(self.user_id, limit=10)
        if facts:
            parts.append("FACTS: " + "; ".join([f"{f.key}={f.value[:30]}" for f in facts]))
        
        return "\n".join(parts)
    
    def cleanup(self) -> Dict:
        """Run forgetting cycle."""
        archived = self.l3.archive_old(self.user_id)
        return {"archived": archived}

class MemoryManager:
    """Manages both user and agent memory layers."""
    
    def __init__(self):
        self.layers: Dict[str, MemoryLayer] = {}
    
    def get_layer(self, layer_type: str, user_id: str = "default") -> MemoryLayer:
        key = f"{layer_type}:{user_id}"
        if key not in self.layers:
            self.layers[key] = MemoryLayer(layer_type, user_id)
        return self.layers[key]
    
    def user_memory(self, user_id: str = "default") -> MemoryLayer:
        return self.get_layer("user", user_id)
    
    def agent_memory(self, user_id: str = "default") -> MemoryLayer:
        return self.get_layer("agent", user_id)
    
    def cleanup_all(self) -> Dict:
        results = {}
        for key, layer in self.layers.items():
            results[key] = layer.cleanup()
        return results

# Global instance
memory_manager = MemoryManager()
