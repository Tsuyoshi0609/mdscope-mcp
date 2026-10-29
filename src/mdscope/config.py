"""Server configuration from environment variables."""

from __future__ import annotations

import os
from pathlib import Path


def allowed_roots() -> list[Path]:
    """Directories the server may read from (MDSCOPE_ALLOWED_ROOTS, ':'-separated)."""
    raw = os.environ.get("MDSCOPE_ALLOWED_ROOTS")
    if raw:
        return [Path(p).expanduser().resolve() for p in raw.split(":") if p]
    return [Path.home().resolve()]


def cache_dir() -> Path:
    """Where generated HTML / PNG go (MDSCOPE_CACHE_DIR, default ~/.cache/mdscope)."""
    d = Path(os.environ.get("MDSCOPE_CACHE_DIR", "~/.cache/mdscope")).expanduser()
    d.mkdir(parents=True, exist_ok=True)
    return d


def check_path(path: str | Path) -> Path:
    """Resolve *path* and raise if it is outside the allowed roots."""
    p = Path(path).expanduser().resolve()
    for root in allowed_roots():
        if p == root or root in p.parents:
            return p
    raise PermissionError(f"{p} is outside MDSCOPE_ALLOWED_ROOTS ({allowed_roots()})")
