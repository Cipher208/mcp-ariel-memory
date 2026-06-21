"""
Authentication — API key + OAuth support for MCP server
"""
import os
import time
import hashlib
import secrets
from typing import Optional, Dict, Any
from pathlib import Path


class APIKeyAuth:
    """Simple API key authentication."""

    def __init__(self, keys_file: str = None):
        self.keys_file = Path(keys_file or str(Path.home() / ".mcp-ariel-memory" / "api_keys.json"))
        self._keys: Dict[str, Dict] = {}
        self._load()

    def _load(self):
        if self.keys_file.exists():
            import json
            try:
                self._keys = json.loads(self.keys_file.read_text(encoding="utf-8"))
            except Exception:
                self._keys = {}

    def _save(self):
        import json
        self.keys_file.parent.mkdir(parents=True, exist_ok=True)
        self.keys_file.write_text(json.dumps(self._keys, indent=2), encoding="utf-8")

    def create_key(self, user_id: str, label: str = "") -> str:
        key = f"ak_{secrets.token_hex(24)}"
        self._keys[key] = {
            "user_id": user_id,
            "label": label,
            "created_at": time.time(),
            "last_used": None,
            "enabled": True,
        }
        self._save()
        return key

    def verify(self, key: str) -> Optional[Dict[str, Any]]:
        if key not in self._keys:
            return None
        entry = self._keys[key]
        if not entry.get("enabled", True):
            return None
        entry["last_used"] = time.time()
        self._save()
        return {"user_id": entry["user_id"], "label": entry.get("label", "")}

    def revoke(self, key: str) -> bool:
        if key in self._keys:
            self._keys[key]["enabled"] = False
            self._save()
            return True
        return False

    def list_keys(self) -> list:
        return [
            {"key": k[:8] + "...", "user_id": v["user_id"], "label": v.get("label", ""),
             "enabled": v.get("enabled", True), "created_at": v["created_at"]}
            for k, v in self._keys.items()
        ]

    def delete_key(self, key: str) -> bool:
        if key in self._keys:
            del self._keys[key]
            self._save()
            return True
        return False


class BearerAuth:
    """Bearer token authentication (for HTTP transport)."""

    def __init__(self):
        self._token = os.environ.get("MCP_AUTH_TOKEN", "")
        if not self._token:
            self._token = f"mt_{secrets.token_hex(32)}"

    def verify(self, auth_header: str) -> bool:
        if not auth_header:
            return False
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            return token == self._token
        return False

    def get_token(self) -> str:
        return self._token


# Singleton
api_key_auth = APIKeyAuth()
bearer_auth = BearerAuth()
