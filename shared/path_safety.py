"""Path traversal prevention — shared guard for all file-accepting functions."""

import os
from pathlib import Path


def safe_resolve(base: Path, user_input: str) -> Path:
    """Resolve user_input relative to base, raising ValueError if it escapes.

    Checks both the base-relative resolution and the real path (follows symlinks).
    """
    base_resolved = base.resolve()
    target = (base / user_input).resolve()

    if not str(target).startswith(str(base_resolved) + os.sep) and target != base_resolved:
        raise ValueError(f"Path escapes base directory: {user_input!r}")

    return target
