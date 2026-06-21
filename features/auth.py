"""
Authentication — API key + persistent Bearer token.
Bearer token сохраняется в файл, переживает рестарт.
"""
import os
import json
import secrets
import time
from pathlib import Path
from typing import Dict, Any, Optional


class APIKeyAuth:
    """API key authentication with file persistence."""

    def __init__(self, keys_file: str = None):
        self.keys_file = Path(keys_file or str(Path.home() / ".mcp-ariel-memory" / "api_keys.json"))
        self._keys: Dict[str, Dict] = {}
        self._load()

    def _load(self):
        if self.keys_file.exists():
            try:
                self._keys = json.loads(self.keys_file.read_text(encoding="utf-8"))
            except Exception:
                self._keys = {}

    def _save(self):
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
    """Bearer token authentication — persistent (сохраняется в файл)."""

    def __init__(self, token_file: str = None):
        self.token_file = Path(token_file or str(Path.home() / ".mcp-ariel-memory" / "bearer_token.json"))
        self._token = self._load_or_create()

    def _load_or_create(self) -> str:
        # 1. Из env переменной
        env_token = os.environ.get("MCP_AUTH_TOKEN", "")
        if env_token:
            return env_token

        # 2. Из файла
        if self.token_file.exists():
            try:
                data = json.loads(self.token_file.read_text(encoding="utf-8"))
                if data.get("token"):
                    return data["token"]
            except Exception:
                pass

        # 3. Создать новый и сохранить
        token = f"mt_{secrets.token_hex(32)}"
        self._save(token)
        return token

    def _save(self, token: str):
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(json.dumps({
            "token": token,
            "created_at": time.time(),
            "note": "Не удалять! Токен переживает рестарт сервера."
        }, indent=2), encoding="utf-8")

    def verify(self, auth_header: str) -> bool:
        if not auth_header:
            return False
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            return token == self._token
        return False

    def get_token(self) -> str:
        return self._token

    def rotate(self) -> str:
        """Создать новый токен (старый перестаёт работать)."""
        import secrets
        self._token = f"mt_{secrets.token_hex(32)}"
        self._save(self._token)
        return self._token


# Singleton
api_key_auth = APIKeyAuth()
bearer_auth = BearerAuth()
