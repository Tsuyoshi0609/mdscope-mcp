"""Assemble viewer pages from the files in viewer/ (no build step).

- standalone page: template.html + CSS + 3Dmol.js + core.js + the JSON payload inlined
- MCP App page:    app.html + CSS + 3Dmol.js + core.js (payload arrives from the host at runtime)

Every payload is also saved as view_<id>.json so an app can fetch it by view_id.
"""

from __future__ import annotations

import hashlib
import html as html_mod
import json
from pathlib import Path

from mdscope.config import cache_dir

VIEWER_DIR = Path(__file__).parent / "viewer"


def _read(name: str) -> str:
    return (VIEWER_DIR / name).read_text(encoding="utf-8")


def _assemble(page: str) -> str:
    return (
        _read(page)
        .replace("/*__CSS__*/", _read("shell.css"))
        .replace("/*__3DMOL__*/", _read("3Dmol-min.js"))
        .replace("/*__CORE__*/", _read("core.js"))
    )


def view_id(payload: dict) -> str:
    return hashlib.sha1(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:10]


def _sources_mtime() -> float:
    return max(p.stat().st_mtime for p in VIEWER_DIR.iterdir())


def render_html(payload: dict) -> str:
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return (
        _assemble("template.html")
        .replace("__TITLE__", html_mod.escape(f"mdscope: {payload.get('title', '')}"))
        .replace("__PAYLOAD_JSON__", data)
    )


def render_app_html() -> str:
    """The MCP App resource (ui://...). Same for every view; data comes from the tool result."""
    return _assemble("app.html")


def write_html(payload: dict, out_dir: Path | None = None) -> Path:
    """Write view_<id>.html (+ .json) into the cache dir; identical payloads reuse the same files."""
    out_dir = out_dir or cache_dir()
    vid = view_id(payload)
    out = out_dir / f"view_{vid}.html"
    # rebuild when the viewer sources (template, core.js, css, 3Dmol) are newer than the file
    if not out.exists() or out.stat().st_mtime < _sources_mtime():
        out.write_text(render_html(payload), encoding="utf-8")
    js = out_dir / f"view_{vid}.json"
    if not js.exists():
        js.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return out


def read_payload(vid: str, out_dir: Path | None = None) -> dict:
    if not vid.isalnum():
        raise ValueError(f"bad view_id {vid!r}")
    p = (out_dir or cache_dir()) / f"view_{vid}.json"
    if not p.is_file():
        raise FileNotFoundError(f"no view with id {vid}; call view_structure again")
    return json.loads(p.read_text(encoding="utf-8"))
