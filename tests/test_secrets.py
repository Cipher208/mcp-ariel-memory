"""Round-trip and backward-compat tests for envelope encryption."""

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True, scope="session")
def master_key_env():
    """Set master key BEFORE importing secrets module."""
    os.environ["MCP_MASTER_KEY"] = "test-secret-for-unit-tests-only"
    from features import secrets

    secrets._master_cache.clear()
    yield
    os.environ.pop("MCP_MASTER_KEY", None)


def test_tampered_ciphertext_rejected():
    from features.secrets import decrypt_json, encrypt_json

    blob = encrypt_json({"x": 1})
    # Flip one bit in the middle of ciphertext
    tampered = bytearray(blob)
    tampered[30] ^= 0x80
    with pytest.raises(Exception):  # nacl.exceptions.CryptoError
        decrypt_json(bytes(tampered))


def test_is_encrypted_blob(tmp_path: Path):
    from features.secrets import is_encrypted_blob

    plain = tmp_path / "plain.json"
    enc = tmp_path / "enc.json"
    plain.write_text('{"a": 1}')
    enc.write_bytes(b"\xab\xcd" * 30)
    assert not is_encrypted_blob(plain)
    assert is_encrypted_blob(enc)


def test_is_encrypted_blob_nonexistent():
    from features.secrets import is_encrypted_blob

    assert not is_encrypted_blob(Path("/nonexistent/file.json"))


def test_save_and_load_dotenv(tmp_path, monkeypatch):
    """_save_dotenv writes to .env, _load_dotenv reads it back."""
    from features.secrets import _load_dotenv, _save_dotenv

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MCP_MASTER_KEY", raising=False)

    _save_dotenv("MCP_MASTER_KEY", "from-dotenv-test")
    env_file = tmp_path / ".env"
    assert env_file.exists()
    assert "MCP_MASTER_KEY=from-dotenv-test" in env_file.read_text()

    _load_dotenv()
    assert os.environ.get("MCP_MASTER_KEY") == "from-dotenv-test"


def test_load_dotenv_skips_comments_and_blanks(tmp_path, monkeypatch):
    """_load_dotenv ignores comments and blank lines."""
    from features.secrets import _load_dotenv

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MCP_MASTER_KEY", raising=False)

    (tmp_path / ".env").write_text("# comment\n\nMCP_MASTER_KEY=real-value\n")
    _load_dotenv()
    assert os.environ.get("MCP_MASTER_KEY") == "real-value"


def test_load_dotenv_does_not_override_existing_env(monkeypatch):
    """_load_dotenv does not overwrite an already-set env var."""
    from features.secrets import _load_dotenv

    monkeypatch.setenv("MCP_MASTER_KEY", "already-set")
    _load_dotenv()
    assert os.environ.get("MCP_MASTER_KEY") == "already-set"


def test_load_master_key_from_env_var(monkeypatch):
    """_load_master_key derives a 32-byte key via argon2id from MCP_MASTER_KEY."""
    from features.secrets import _load_master_key, _master_cache

    monkeypatch.setenv("MCP_MASTER_KEY", "my-secret-seed-for-kdf")
    _master_cache.clear()

    key = _load_master_key()
    assert isinstance(key, bytes)
    assert len(key) == 32


def test_load_master_key_auto_generates(monkeypatch, tmp_path):
    """_load_master_key auto-generates when no key source is available."""
    from features.secrets import _load_master_key, _master_cache

    monkeypatch.delenv("MCP_MASTER_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MCP_MASTER_KEY", raising=False)
    _master_cache.clear()

    key = _load_master_key()
    assert isinstance(key, bytes)
    assert len(key) == 32
    # Auto-generated key is saved to .env
    env_file = tmp_path / ".env"
    assert env_file.exists()
    assert "MCP_MASTER_KEY=" in env_file.read_text()


def test_get_master_key_caches():
    """_get_master_key returns the same key on repeated calls."""
    from features.secrets import _get_master_key, _master_cache

    _master_cache.clear()
    key1 = _get_master_key()
    key2 = _get_master_key()
    assert key1 is key2  # same object from cache
