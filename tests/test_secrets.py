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


def test_encrypt_decrypt_roundtrip():
    from features.secrets import decrypt_json, encrypt_json

    payload = {"alice": "ak_abc", "bob": "ak_def"}
    blob = encrypt_json(payload)
    assert decrypt_json(blob) == payload


def test_different_nonces_per_call():
    from features.secrets import encrypt_json
    a = encrypt_json({"x": 1})
    b = encrypt_json({"x": 1})
    assert a != b  # different nonce → different ciphertext


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
