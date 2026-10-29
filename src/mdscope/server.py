"""FastMCP server entry point. Tools are registered here; logic lives in sibling modules."""

from __future__ import annotations

import logging
import sys

from fastmcp import FastMCP

from mdscope import __version__
from mdscope.config import allowed_roots, cache_dir

mcp = FastMCP("mdscope")


@mcp.tool
def mdscope_info() -> dict:
    """Return server version, allowed roots and cache directory (self-check)."""
    return {
        "version": __version__,
        "allowed_roots": [str(p) for p in allowed_roots()],
        "cache_dir": str(cache_dir()),
    }


def main() -> None:
    # stdout is reserved for MCP; everything else goes to stderr and a log file
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stderr),
            logging.FileHandler(cache_dir() / "server.log"),
        ],
    )
    if "--check" in sys.argv:
        print(mdscope_info.fn(), file=sys.stderr)
        return
    mcp.run()


if __name__ == "__main__":
    main()
