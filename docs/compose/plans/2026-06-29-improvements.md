# mcp-ariel-memory Improvement Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve code quality, security, performance, and CI/CD for mcp-ariel-memory

**Architecture:** Fix tech debt in test infrastructure, split large files, harden error handling, optimize KDF caching, improve CI

**Tech Stack:** Python 3.10-3.13, pytest, pynacl, aiosqlite, GitHub Actions

## Global Constraints

- Python 3.10+ (all changes must be compatible)
- 158 tests must pass after each task
- ruff check + ruff format must pass
- No breaking changes to MCP tool interface
- Encrypt all sensitive data at rest

---

### Task 1: Fix asyncio.run() at module level in test_all.py

**Files:**
- Modify: `tests/test_all.py:31`

**Interfaces:**
- Consumes: `_setup()` function
- Produces: pytest-compatible async fixture

- [ ] **Step 1: Move asyncio.run() into fixture**

Replace module-level `asyncio.run(_setup())` with a session-scoped async fixture.

- [ ] **Step 2: Run tests to verify**

Run: `pytest tests/test_all.py -v`
Expected: All 10 tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/test_all.py
git commit -m "fix: move asyncio.run() from module level to fixture"
```

---

### Task 2: Add logging for _load() encryption errors

**Files:**
- Modify: `features/auth.py:40-46`
- Modify: `features/auth.py:147-148`

**Interfaces:**
- Consumes: `logging` module
- Produces: error logs on encryption failure

- [ ] **Step 1: Add logging to _load()**

```python
except Exception as e:
    import logging
    logging.getLogger(__name__).warning(f"Failed to encrypt legacy file {self.keys_file}: {e}")
    pass
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/test_auth_crypto.py -v`
Expected: All 4 tests pass

- [ ] **Step 3: Commit**

```bash
git add features/auth.py
git commit -m "feat: log encryption errors in _load() for debugging"
```

---

### Task 3: Wrap os.chmod in try/except for Windows compatibility

**Files:**
- Modify: `features/auth.py:59-62`
- Modify: `features/auth.py:64-67`
- Modify: `features/auth.py:164-167`
- Modify: `features/auth.py:169-172`

**Interfaces:**
- Consumes: `os.chmod()`
- Produces: graceful handling on Windows

- [ ] **Step 1: Wrap chmod calls**

Already done in previous commit. Verify it's correct.

- [ ] **Step 2: Run tests**

Run: `pytest tests/test_auth_crypto.py tests/test_secrets.py -v`
Expected: All 9 tests pass

- [ ] **Step 3: Commit (if changes needed)**

---

### Task 4: Add pytest-xdist for parallel test execution

**Files:**
- Modify: `pyproject.toml:36-40`

**Interfaces:**
- Consumes: pytest
- Produces: parallel test execution

- [ ] **Step 1: Add pytest-xdist to dev dependencies**

```toml
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-xdist>=3.0",
    "ruff>=0.1",
]
```

- [ ] **Step 2: Run tests with -n auto**

Run: `pytest tests/ -n auto -v`
Expected: All 158 tests pass (faster)

- [ ] **Step 3: Update CI to use -n auto**

Modify `.github/workflows/ci.yml`:
```yaml
- run: pytest tests/ -v --tb=long -n auto
```

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml .github/workflows/ci.yml
git commit -m "ci: add pytest-xdist for parallel test execution"
```

---

### Task 5: Document config.yaml security warnings

**Files:**
- Modify: `docs/09-features.md:1062-1077`
- Modify: `docs/10-shared.md:1439-1451`

**Interfaces:**
- Consumes: existing docs
- Produces: security warnings for config.yaml

- [ ] **Step 1: Add security warning to config section**

```markdown
### Security Warning

`config.yaml` may contain `crypto.master_key_hex` in plaintext. For production:

1. Use OS keychain instead (recommended)
2. Or set `MCP_MASTER_KEY` environment variable
3. Never commit `config.yaml` with real keys to version control
```

- [ ] **Step 2: Run ruff check**

Run: `ruff check docs/`
Expected: No errors (docs are not Python)

- [ ] **Step 3: Commit**

```bash
git add docs/09-features.md docs/10-shared.md
git commit -m "docs: add security warnings for config.yaml key storage"
```

---

### Task 6: Add keyring as default master key source

**Files:**
- Modify: `features/secrets.py:38-74`

**Interfaces:**
- Consumes: `keyring` library
- Produces: keyring-first resolution

- [ ] **Step 1: Reorder resolution to keyring first**

```python
def _load_master_key() -> bytes:
    # 1. Try OS keychain (recommended)
    try:
        import keyring
        stored = keyring.get_password(_KEYRING_SERVICE, _KEYRING_USERNAME)
        if stored:
            return bytes.fromhex(stored)
    except Exception:
        pass

    # 2. Try config
    try:
        from config import config
        cfg_key = config.get("crypto", "master_key_hex", default="")
        if cfg_key:
            return bytes.fromhex(cfg_key)
    except Exception:
        pass

    # 3. Try environment variable
    env_seed = os.environ.get(_ENV_VAR)
    if env_seed:
        return argon2id.kdf(...)

    raise RuntimeError("No master key found...")
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/test_secrets.py -v`
Expected: All 5 tests pass

- [ ] **Step 3: Commit**

```bash
git add features/secrets.py
git commit -m "feat: prefer keyring over env var for master key resolution"
```

---

### Task 7: Add requirements.txt for reproducible builds

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`

**Interfaces:**
- Consumes: pyproject.toml dependencies
- Produces: pinned dependency files

- [ ] **Step 1: Generate requirements.txt**

```bash
pip freeze > requirements.txt
```

- [ ] **Step 2: Generate requirements-dev.txt**

```bash
pip install -e ".[dev]" && pip freeze > requirements-dev.txt
```

- [ ] **Step 3: Add .gitignore entry**

Add `requirements*.txt` to `.gitignore` if not already there.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt requirements-dev.txt .gitignore
git commit -m "ci: add pinned requirements for reproducible builds"
```

---

### Task 8: Split mcp_server.py into modules (optional, large)

**Files:**
- Create: `mcp_server/__init__.py`
- Create: `mcp_server/tools.py`
- Create: `mcp_server/handlers.py`
- Modify: `pyproject.toml:57-58`

**Interfaces:**
- Consumes: existing mcp_server.py
- Produces: modular structure

- [ ] **Step 1: Create module structure**

- [ ] **Step 2: Move tool definitions to tools.py**

- [ ] **Step 3: Move handlers to handlers.py**

- [ ] **Step 4: Update imports**

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_mcp/ -v`
Expected: All MCP tests pass

- [ ] **Step 6: Commit**

```bash
git add mcp_server/
git commit -m "refactor: split mcp_server.py into tools and handlers modules"
```

---

## Execution Order

1. Task 1: Fix asyncio.run() (quick win, test infrastructure)
2. Task 2: Add logging (security, debugging)
3. Task 3: Verify os.chmod (already done, just verify)
4. Task 4: Add pytest-xdist (CI performance)
5. Task 5: Document security (docs)
6. Task 6: Reorder keyring (security)
7. Task 7: Add requirements.txt (reproducibility)
8. Task 8: Split mcp_server.py (optional, large refactor)

**Estimated time:** 30-45 minutes for tasks 1-7, additional 30 minutes for task 8
