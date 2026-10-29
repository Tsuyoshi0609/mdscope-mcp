"""Static HTTP server for the cache dir, so clients without an Artifact feature (Codex) can
open generated viewers in a browser. Started with `mdscope-mcp --serve`."""

from __future__ import annotations

import functools
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # keep stdout clean (MCP convention), log to stderr
        sys.stderr.write(f"{self.address_string()} - {fmt % args}\n")


def serve(directory: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    handler = functools.partial(_QuietHandler, directory=str(directory))
    with ThreadingHTTPServer((host, port), handler) as httpd:
        print(f"serving {directory} at http://{host}:{port}/  (Ctrl-C to stop)", file=sys.stderr)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


def view_url(filename: str) -> str | None:
    """URL of a generated file if MDSCOPE_VIEW_URL (e.g. http://host:8765) is set, else None."""
    base = os.environ.get("MDSCOPE_VIEW_URL")
    return f"{base.rstrip('/')}/{filename}" if base else None
