"""FastMCP server entry point. Tools are registered here; logic lives in sibling modules."""

from __future__ import annotations

import argparse
import logging
import sys

from fastmcp import FastMCP
from fastmcp.apps import AppConfig, ResourceCSP
from fastmcp.tools import ToolResult

from mdscope import __version__, loader, payload, registry
from mdscope.config import allowed_roots, cache_dir
from mdscope.html import read_payload, render_app_html, view_id, write_html
from mdscope.serve import serve, view_url

mcp = FastMCP("mdscope")

# MCP Apps UI resource. Bump the version in the URI when the page changes incompatibly
# (hosts cache ui:// resources).
VIEWER_URI = "ui://mdscope/viewer/v2.html"
PAYLOAD_KEY = "mdscope/payload"

SHOW_HINT = (
    "If the host rendered an inline 3D viewer, nothing else is needed. Otherwise: in Claude Code, "
    "publish artifacts[0].path with the Artifact tool (self-contained HTML); else give the user "
    "artifacts[0].url if present (served by `mdscope-mcp --serve`), else the file path."
)


def info() -> dict:
    return {
        "version": __version__,
        "allowed_roots": [str(p) for p in allowed_roots()],
        "cache_dir": str(cache_dir()),
        "loaded_systems": [{"system_id": s.system_id, "name": s.name} for s in registry.list_systems()],
    }


@mcp.resource(VIEWER_URI, app=AppConfig(csp=ResourceCSP(resource_domains=[]), prefers_border=True))
def viewer_app() -> str:
    """Interactive 3D structure viewer (MCP App). 3Dmol.js is inlined; no network access needed."""
    return render_app_html()


@mcp.tool
def mdscope_info() -> dict:
    """Return server version, allowed roots, cache directory and loaded systems (self-check)."""
    return info()


PATH_NOTE = (
    "Paths are on the machine where mdscope-mcp runs (possibly a remote host reached over SSH), "
    "not on the client's machine; do not check them with local shell commands, use list_files."
)


@mcp.tool
def list_files(path: str = "~", pattern: str = "*", max_entries: int = 200) -> dict:
    """List files on the mdscope server host (structure/trajectory files and directories), within
    the allowed roots. pattern is a glob such as '*.pdb' or '*.xtc'. Use this to find or verify
    paths before load_system / view_structure."""
    from mdscope.config import check_path

    root = check_path(path)
    if not root.is_dir():
        raise NotADirectoryError(f"{root} is not a directory")
    entries = []
    for p in sorted(root.glob(pattern)):
        if p.name.startswith("."):
            continue
        st = p.stat()
        entries.append({"name": p.name, "dir": p.is_dir(), "size_mb": round(st.st_size / 1e6, 3)})
        if len(entries) >= max_entries:
            break
    return {"path": str(root), "entries": entries, "truncated": len(entries) >= max_entries}


@mcp.tool
def load_system(topology: str, trajectory: str | list[str] | None = None, name: str | None = None) -> dict:
    """Load a structure file (.pdb/.gro/.cif/.tpr/.prmtop ...) and optionally trajectory file(s)
    (.xtc/.trr/.dcd/.nc ...). Returns a system_id and a composition summary (chains, ligands,
    frames). Use the summary to write selection strings for view_structure. """ + PATH_NOTE
    system = loader.load(topology, trajectory, name)
    return loader.summarize(system)


@mcp.tool
def describe_system(system_id: str) -> dict:
    """Composition of a loaded system: protein chains with residue ranges and sequences, ligand
    candidates, water/ion counts, trajectory length. Selection syntax is MDAnalysis
    (e.g. 'protein', 'segid A and resid 10:50', 'resname LIG', 'around 5 resname LIG')."""
    return loader.summarize(registry.get(system_id))


VIEW_TOOL_META = {
    "openai/outputTemplate": VIEWER_URI,
    "openai/toolInvocation/invoking": "Building 3D view",
    "openai/toolInvocation/invoked": "3D view ready",
}
# payload keys the model does not need (coordinates and viewer internals)
_HIDDEN = ("pdb", "coords_b64", "highlight_serials", "notes", "frame_indices", "times_ps", "coord_scale")


def _system(system_id, topology, trajectory):
    if system_id is None and topology is None:
        raise ValueError("give system_id or topology")
    return registry.get(system_id) if system_id else loader.load(topology, trajectory)


def _respond(system, data: dict, what: str) -> ToolResult:
    """Write the standalone HTML and build the tool result shared by the view_* tools."""
    html_path = write_html(data)
    summary = {k: v for k, v in data.items() if k not in _HIDDEN}
    summary["view_id"] = view_id(data)
    summary["html_size_mb"] = round(html_path.stat().st_size / 1e6, 2)
    if "times_ps" in data:
        summary["time_span_ps"] = [data["times_ps"][0], data["times_ps"][-1]]
    artifact = {"kind": "html", "path": str(html_path), "caption": f"{data['title']}: {what}"}
    if url := view_url(html_path.name):
        artifact["url"] = url
    structured = {
        "summary": summary,
        "artifacts": [artifact],
        "warnings": data["notes"] + system.warnings,
        "how_to_show": SHOW_HINT,
    }
    text = (
        f"{data['title']}: {data['n_residues']} residues, {data['n_atoms']} atoms, {what} "
        f"({data['style']}/{data['color']}). HTML: {html_path}"
        + (f" URL: {artifact['url']}" if "url" in artifact else "")
    )
    # the viewer payload rides in _meta: delivered to the app, hidden from the model
    return ToolResult(content=text, structured_content=structured, meta={PAYLOAD_KEY: data})


@mcp.tool(app=AppConfig(resource_uri=VIEWER_URI), meta=VIEW_TOOL_META)
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
    pbc: bool | None = None,
) -> ToolResult:
    """Show an interactive 3D viewer (rotate/zoom) for one frame of a loaded system. Hosts that
    support MCP Apps (ChatGPT, Claude Desktop) render it inline; others get a self-contained HTML
    file path/URL. Give either system_id (from load_system) or topology (+ trajectory) to load on
    the fly. selection: MDAnalysis selection of atoms to show (default 'protein'; bound ligands are
    added automatically). style: cartoon|sticks|spheres|lines. color: ss|chain|rainbow|element.
    highlight: optional selection drawn as magenta sticks on top. pbc: make molecules whole across
    periodic boundaries (default: only when a trajectory is loaded). For playback of several
    frames use view_trajectory. """ + PATH_NOTE
    system = _system(system_id, topology, trajectory)
    data = payload.build_payload(system, selection, frame, style, color, highlight, title, pbc)
    return _respond(system, data, f"selection '{selection}', frame {frame}")


@mcp.tool(app=AppConfig(resource_uri=VIEWER_URI), meta=VIEW_TOOL_META)
def view_trajectory(
    system_id: str | None = None,
    topology: str | None = None,
    trajectory: str | list[str] | None = None,
    selection: str = "protein",
    start: int = 0,
    stop: int | None = None,
    stride: int | None = None,
    max_frames: int = 50,
    style: str = "cartoon",
    color: str = "ss",
    highlight: str | None = None,
    title: str | None = None,
    pbc: bool = True,
    align: bool = True,
    max_payload_mb: float = 8.0,
) -> ToolResult:
    """Show an interactive 3D viewer with a frame slider and play button for an MD trajectory.
    Frames start:stop:stride are thinned evenly to at most max_frames (default 50) and further if
    the coordinates would exceed max_payload_mb. Molecules are made whole across periodic
    boundaries (pbc), centered, and aligned on CA atoms to the first frame (align) so the motion is
    easy to see. Other arguments as in view_structure. For a large system narrow the selection
    (e.g. 'protein and not name H*') rather than raising max_payload_mb. """ + PATH_NOTE
    system = _system(system_id, topology, trajectory)
    data = payload.build_trajectory_payload(
        system, selection, start, stop, stride, max_frames, style, color, highlight, title,
        pbc, align, max_payload_mb,
    )
    n = data.get("n_frames", 1)
    what = f"selection '{selection}', {n} frames {data['frame']}..{data.get('frame_indices', [data['frame']])[-1]}"
    return _respond(system, data, what)


@mcp.tool(app=AppConfig(visibility=["app"]))
def get_view_payload(view_id: str) -> dict:
    """Return the viewer payload (PDB text + display settings) of a previous view_structure call.
    Used by the viewer app when the host does not forward tool-result metadata."""
    return read_payload(view_id)


def main() -> None:
    ap = argparse.ArgumentParser(prog="mdscope-mcp", description="MCP server for viewing MD structures")
    ap.add_argument("--check", action="store_true", help="print self-check info to stderr and exit")
    ap.add_argument("--serve", action="store_true", help="serve the cache dir over HTTP instead of running MCP")
    ap.add_argument("--host", default="127.0.0.1", help="bind address for --serve (default 127.0.0.1)")
    ap.add_argument("--port", type=int, default=8765, help="port for --serve (default 8765)")
    args = ap.parse_args()
    # stdout is reserved for MCP; everything else goes to stderr and a log file
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stderr),
            logging.FileHandler(cache_dir() / "server.log"),
        ],
    )
    if args.check:
        print(info(), file=sys.stderr)
        return
    if args.serve:
        serve(cache_dir(), args.host, args.port)
        return
    mcp.run()


if __name__ == "__main__":
    main()
