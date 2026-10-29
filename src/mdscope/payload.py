"""Turn a System into the data the viewer HTML needs: a PDB string plus display settings."""

from __future__ import annotations

import os
import tempfile
import warnings

import MDAnalysis as mda
from MDAnalysis.exceptions import SelectionError

from mdscope.config import cache_dir
from mdscope.loader import LIGAND_SEL
from mdscope.registry import System

STYLES = ("cartoon", "sticks", "spheres", "lines")
COLORS = ("ss", "chain", "rainbow", "element")


def select(system: System, selection: str) -> mda.AtomGroup:
    """Evaluate a selection string; on error, re-raise with hints for the LLM."""
    try:
        ag = system.universe.select_atoms(selection)
    except (SelectionError, ValueError, TypeError) as e:
        raise ValueError(
            f"invalid selection {selection!r}: {e}. Examples: 'protein', 'protein and name CA', "
            f"'resname LIG', 'around 5 resname LIG', 'segid A and resid 10:50'"
        ) from None
    if ag.n_atoms == 0:
        raise ValueError(f"selection {selection!r} matched no atoms; call describe_system for names")
    return ag


def _to_pdb(ag: mda.AtomGroup) -> str:
    # MDAnalysis' PDB writer wants a filename, so round-trip through the cache dir
    fd, tmp = tempfile.mkstemp(suffix=".pdb", dir=cache_dir())
    os.close(fd)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ag.write(tmp)
        with open(tmp) as f:
            return f.read()
    finally:
        os.unlink(tmp)


def build_payload(
    system: System,
    selection: str = "protein",
    frame: int = 0,
    style: str = "cartoon",
    color: str = "ss",
    highlight: str | None = None,
    title: str | None = None,
) -> dict:
    if style not in STYLES:
        raise ValueError(f"style must be one of {STYLES}")
    if color not in COLORS:
        raise ValueError(f"color must be one of {COLORS}")
    u = system.universe
    n_frames = len(u.trajectory)
    if not 0 <= frame < n_frames:
        raise ValueError(f"frame {frame} out of range 0..{n_frames - 1}")
    u.trajectory[frame]

    notes: list[str] = []
    ag = select(system, selection)
    if selection.strip() == "protein":
        # the default view should show bound ligands too
        lig = u.select_atoms(LIGAND_SEL)
        if lig.n_atoms:
            ag = ag | lig
            notes.append(f"included {len(lig.residues)} non-protein residue(s) as ligands")

    highlight_serials: list[int] = []
    if highlight:
        hl = select(system, highlight)
        inside = hl & ag
        if inside.n_atoms < hl.n_atoms:
            notes.append(f"{hl.n_atoms - inside.n_atoms} highlighted atom(s) are outside the selection and not shown")
        # serial numbers in the written PDB are 1..N in selection order
        index_of = {ix: i + 1 for i, ix in enumerate(ag.indices)}
        highlight_serials = [index_of[ix] for ix in inside.indices]

    return {
        "title": title or system.name,
        "system_id": system.system_id,
        "selection": selection,
        "frame": frame,
        "n_frames_total": n_frames,
        "n_atoms": int(ag.n_atoms),
        "n_residues": int(ag.residues.n_residues),
        "style": style,
        "color": color,
        "highlight": highlight,
        "highlight_serials": highlight_serials,
        "pdb": _to_pdb(ag),
        "notes": notes,
    }
