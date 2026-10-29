"""Write a self-contained viewer HTML: template + inlined 3Dmol.js + JSON payload."""

from __future__ import annotations

import hashlib
import html as html_mod
import json
from pathlib import Path

from mdscope.config import cache_dir

VIEWER_DIR = Path(__file__).parent / "viewer"
TEMPLATE = VIEWER_DIR / "template.html"
LIB = VIEWER_DIR / "3Dmol-min.js"


def render_html(payload: dict) -> str:
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return (
        TEMPLATE.read_text(encoding="utf-8")
        .replace("__TITLE__", html_mod.escape(f"mdscope: {payload.get('title', '')}"))
        .replace("/*__3DMOL__*/", LIB.read_text(encoding="utf-8"))
        .replace("__PAYLOAD_JSON__", data)
    )


def write_html(payload: dict, out_dir: Path | None = None) -> Path:
    """Write view_<hash>.html into the cache dir; identical payloads reuse the same file."""
    key = hashlib.sha1(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:10]
    out = (out_dir or cache_dir()) / f"view_{key}.html"
    if not out.exists():
        out.write_text(render_html(payload), encoding="utf-8")
    return out
