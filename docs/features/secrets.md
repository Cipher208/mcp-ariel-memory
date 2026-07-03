# Encryption

## Envelope Encryption

All sensitive data (API keys, tokens, saga state) encrypted at rest using libsodium secretbox.

```python
from features.secrets import encrypt_json, decrypt_json

# Encrypt
blob = encrypt_json({"token": "secret", "created_at": 1234567890})
# blob = nonce(24) + ciphertext (binary)

# Decrypt
data = decrypt_json(blob)
# data = {"token": "secret", "created_at": 1234567890}
```

## Key Resolution

1. OS keychain (keyring) — production
2. config.yaml (`crypto.master_key_hex`)
3. .env file (`MCP_MASTER_KEY=...`) — development
4. Environment variable
5. Auto-generate (saves to .env)

## File Format

```
[nonce 24 bytes][ciphertext...]
```

## is_encrypted_blob

Check if a file is encrypted (heuristic):

```python
from features.secrets import is_encrypted_blob
from pathlib import Path

is_encrypted_blob(Path("bearer_token.json"))  # True if encrypted
```
