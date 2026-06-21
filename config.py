"""
Universal Memory MCP Server
Two-layer unified memory: Layer 1 (user) + Layer 2 (agent identity)
"""
import yaml
from pathlib import Path

class Config:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance
    
    def _load(self):
        config_path = Path(__file__).parent / "config.yaml"
        with open(config_path) as f:
            self._data = yaml.safe_load(f)
    
    def get(self, *keys, default=None):
        value = self._data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key, default)
            else:
                return default
        return value
    
    def is_hook_enabled(self, layer: str, hook: str) -> bool:
        return self.get("hooks", layer, hook, default=False)
    
    def is_feature_enabled(self, feature: str) -> bool:
        return self.get("features", feature, default=False)
    
    def get_wiki_types(self, layer: str) -> list:
        return self.get("wiki", layer, default=[])
    
    def get_limit(self, key: str) -> int:
        return self.get("limits", key, default=0)
    
    def get_forgetting(self, key: str) -> float:
        return self.get("forgetting", key, default=0.0)

config = Config()
