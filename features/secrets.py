"""Envelope-encrypt JSON secrets (api_keys, bearer tokens, saga state).

Master key resolution order:
1. crypto.master_key_hex in config.yaml
2. OS keychain (keyring library)
3. MCP_MASTER_KEY environment variable (argon2id KDF)
4. Fail loud if none available
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

try:
    from nacl.secret import SecretBox
    from nacl.pwhash import argon2id
    from nacl.utils import random as nacl_random

    _HAS_NACL = True
except ImportError:
    _HAS_NACL = False


_KEYRING_SERVICE = "mcp-ariel-memory"
_KEYRING_USERNAME = "master-key"
_ENV_VAR = "MCP_MASTER_KEY"
_KDF_SALT = b"ariel-memory-v1\x00"
_MASTER_KEY_LEN = 32

# File format: [nonce 24B][ciphertext...]
_NONCE_SIZE = 24
_MAC_SIZE = 16


def _load_master_key() -> bytes:
    """Load or derive master key from config, keyring, or environment."""
    if not _HAS_NACL:
        raise ImportError("pynacl is required for encryption. Install with: pip install pynacl")

    # Try config first
    try:
        from config import config

        cfg_key = config.get("crypto", "master_key_hex", default="")
        if cfg_key:
            return bytes.fromhex(cfg_key)
    except Exception:
        pass

    # Try OS keychain
    try:
        import keyring

        stored = keyring.get_password(_KEYRING_SERVICE, _KEYRING_USERNAME)
        if stored:
            return bytes.fromhex(stored)
    except Exception:
        pass

    # Try environment variable with argon2id KDF
    env_seed = os.environ.get(_ENV_VAR)
    if env_seed:
        return argon2id.kdf(
            size=_MASTER_KEY_LEN,
            password=env_seed.encode("utf-8"),
            salt=_KDF_SALT,
            opslimit=argon2id.OPSLIMIT_MODERATE,
            memlimit=argon2id.MEMLIMIT_MODERATE,
        )

    raise RuntimeError("No master key found. Set MCP_MASTER_KEY env var, store in OS keychain, or set crypto.master_key_hex in config.yaml")


_master_cache: dict[str, bytes] = {}


def _get_master_key() -> bytes:
    """Get cached master key."""
    key = _master_cache.get("k")
    if key is None:
        key = _load_master_key()
        _master_cache["k"] = key
    return key


def encrypt_json(data: dict | list) -> bytes:
    """Encrypt JSON data. Returns nonce(24) || ciphertext."""
    box = SecretBox(_get_master_key())
    nonce = nacl_random(SecretBox.NONCE_SIZE)
    plaintext = json.dumps(data, ensure_ascii=False, sort_keys=True).encode()
    return nonce + box.encrypt(plaintext, nonce).ciphertext


def decrypt_json(blob: bytes) -> Any:
    """Decrypt blob back to JSON."""
    if len(blob) < _NONCE_SIZE + _MAC_SIZE:
        raise ValueError("blob too short for valid SecretBox message")
    nonce, ct = blob[:_NONCE_SIZE], blob[_NONCE_SIZE:]
    box = SecretBox(_get_master_key())
    return json.loads(box.decrypt(ct, nonce).decode("utf-8"))


def is_encrypted_blob(path: Path) -> bool:
    """Check if file is encrypted (not plain JSON).

    Heuristic: encrypted blobs start with random 24 bytes (nonce),
    JSON starts with { or [.
    """
    if not path.exists():
        return False
    with open(path, "rb") as f:
        head = f.read(1)
    return head not in (b"{", b"[", b" ", b"\n")


def install_master_key_to_keychain(hex_key: str) -> None:
    """Store master key in OS keychain (run once during setup)."""
    bytes.fromhex(hex_key)  # validate
    import keyring

    keyring.set_password(_KEYRING_SERVICE, _KEYRING_USERNAME, hex_key)
