"""End-to-end tests for auth with encryption."""

import json
import os


def test_legacy_plain_json_gets_rotated(tmp_path):
    """If file is plain JSON, it should be auto-encrypted on load."""
    keys_file = tmp_path / "api_keys.json"
    keys_file.write_text(json.dumps({"ak_old": {"user_id": "u1", "label": "old", "enabled": True, "created_at": 1.0}}))
    from features.auth import APIKeyAuth

    auth = APIKeyAuth(keys_file=str(keys_file))
    keys = auth.list_keys()
    assert len(keys) == 1
    assert keys[0]["user_id"] == "u1"

    # File should now be encrypted
    raw = keys_file.read_bytes()
    assert raw[:1] not in (b"{", b"[")


def test_create_then_verify_round_trip(tmp_path):
    keys_file = tmp_path / "api_keys.json"
    from features.auth import APIKeyAuth

    auth = APIKeyAuth(keys_file=str(keys_file))
    key = auth.create_key("alice", "test-key")
    out = auth.verify(key)
    assert out == {"user_id": "alice", "label": "test-key"}


def test_wrong_master_key_fails(tmp_path):
    keys_file = tmp_path / "api_keys.json"
    from features.auth import APIKeyAuth

    auth = APIKeyAuth(keys_file=str(keys_file))
    auth.create_key("bob")

    # Change master key
    os.environ["MCP_MASTER_KEY"] = "different-secret"
    from features import secrets

    secrets._master_cache.clear()

    # Should fail to decrypt (returns empty dict, not exception)
    auth2 = APIKeyAuth(keys_file=str(keys_file))
    assert auth2.list_keys() == []  # cannot read old keys


def test_bearer_token_encrypted(tmp_path):
    token_file = tmp_path / "bearer_token.json"
    from features.auth import BearerAuth

    auth = BearerAuth(token_file=str(token_file))
    token = auth.get_token()
    assert token.startswith("mt_")

    # File should be encrypted
    raw = token_file.read_bytes()
    assert raw[:1] not in (b"{", b"[")

    # Verify works
    assert auth.verify(f"Bearer {token}") is True
    assert auth.verify("Bearer invalid") is False
