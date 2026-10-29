"""FastMCP server entry point. Tools are registered here; logic lives in sibling modules."""

from __future__ import annotations

import logging
import sys

from fastmcp import FastMCP

from mdscope import __version__, loader, payload, registry
from mdscope.config import allowed_roots, cache_dir
from mdscope.html import write_html

mcp = FastMCP("mdscope")

SHOW_HINT = (
    "To show the viewer to the user: in Claude Code, publish artifacts[0].path with the Artifact "
    "tool (it is a self-contained HTML page); otherwise tell the user to open that file in a browser."
)


def info() -> dict:
    return {
        "version": __version__,
        "allowed_roots": [str(p) for p in allowed_roots()],
        "cache_dir": str(cache_dir()),
        "loaded_systems": [{"system_id": s.system_id, "name": s.name} for s in registry.list_systems()],
    }


@mcp.tool
def mdscope_info() -> dict:
    """Return server version, allowed roots, cache directory and loaded systems (self-check)."""
    return info()


@mcp.tool
def load_system(topology: str, trajectory: str | list[str] | None = None, name: str | None = None) -> dict:
    """Load a structure file (.pdb/.gro/.cif/.tpr/.prmtop ...) and optionally trajectory file(s)
    (.xtc/.trr/.dcd/.nc ...). Returns a system_id and a composition summary (chains, ligands,
    frames). Use the summary to write selection strings for view_structure."""
    system = loader.load(topology, trajectory, name)
    return loader.summarize(system)


@mcp.tool
def describe_system(system_id: str) -> dict:
    """Composition of a loaded system: protein chains with residue ranges and sequences, ligand
    candidates, water/ion counts, trajectory length. Selection syntax is MDAnalysis
    (e.g. 'protein', 'segid A and resid 10:50', 'resname LIG', 'around 5 resname LIG')."""
    return loader.summarize(registry.get(system_id))


@mcp.tool
def view_structure(
    system_id: str | None = None,
    topology: str | None = None,
    trajectory: str | list[str] | None = None,
    selection: str = "protein",
    frame: int = 0,
    style: str = "cartoon",
    color: str = "ss",
    highlight: str | None = None,
    title: str | None = None,
) -> dict:
    """Write an interactive 3D viewer (self-contained HTML, rotate/zoom in a browser) for one frame
    of a loaded system. Give either system_id (from load_system) or topology (+ trajectory) to load
    on the fly. selection: MDAnalysis selection of atoms to show (default 'protein'; bound ligands
    are added automatically). style: cartoon|sticks|spheres|lines. color: ss|chain|rainbow|element.
    highlight: optional selection drawn as magenta sticks on top. The result lists the HTML path
    under artifacts; see how_to_show."""
    if system_id is None and topology is None:
        raise ValueError("give system_id or topology")
    system = registry.get(system_id) if system_id else loader.load(topology, trajectory)
    data = payload.build_payload(system, selection, frame, style, color, highlight, title)
    html_path = write_html(data)
    summary = {k: v for k, v in data.items() if k not in ("pdb", "highlight_serials", "notes")}
    summary["html_size_mb"] = round(html_path.stat().st_size / 1e6, 2)
    return {
        "summary": summary,
        "artifacts": [
            {"kind": "html", "path": str(html_path), "caption": f"{data['title']}: {selection}, frame {frame}"}
        ],
        "warnings": data["notes"] + system.warnings,
        "how_to_show": SHOW_HINT,
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
        print(info(), file=sys.stderr)
        return
    mcp.run()


if __name__ == "__main__":
    main()
