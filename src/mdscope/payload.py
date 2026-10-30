"""Turn a System into the data the viewer HTML needs: a PDB string, optional trajectory
coordinates (int16, base64) and display settings."""

from __future__ import annotations

import os
import tempfile
import warnings

import MDAnalysis as mda
import numpy as np
from MDAnalysis.exceptions import SelectionError

from mdscope import trajectory
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


def _atoms(system: System, selection: str, highlight: str | None, notes: list[str]) -> tuple[mda.AtomGroup, list[int]]:
    ag = select(system, selection)
    if selection.strip() == "protein":
        # the default view should show bound ligands too
        lig = system.universe.select_atoms(LIGAND_SEL)
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
    return ag, highlight_serials


def _build(
    system: System,
    indices: np.ndarray,
    selection: str,
    style: str,
    color: str,
    highlight: str | None,
    title: str | None,
    pbc: bool,
    align: bool,
    max_payload_mb: float,
    notes: list[str],
) -> dict:
    if style not in STYLES:
        raise ValueError(f"style must be one of {STYLES}")
    if color not in COLORS:
        raise ValueError(f"color must be one of {COLORS}")
    u = system.universe
    ag, highlight_serials = _atoms(system, selection, highlight, notes)
    fr = trajectory.extract(u, ag, indices, pbc=pbc, align=align, max_payload_mb=max_payload_mb)
    notes.extend(fr.notes)

    # the PDB carries the processed first frame so single-frame and trajectory views agree
    u.trajectory[fr.indices[0]]
    ag.positions = fr.coords[0]
    pdb = _to_pdb(ag)

    data = {
        "title": title or system.name,
        "system_id": system.system_id,
        "selection": selection,
        "frame": fr.indices[0],
        "n_frames_total": len(u.trajectory),
        "n_atoms": int(ag.n_atoms),
        "n_residues": int(ag.residues.n_residues),
        "style": style,
        "color": color,
        "highlight": highlight,
        "highlight_serials": highlight_serials,
        "pbc": fr.pbc_applied,
        "pdb": pdb,
        "notes": notes,
    }
    if fr.n_frames > 1:
        data.update(
            {
                "n_frames": fr.n_frames,
                "frame_indices": fr.indices,
                "times_ps": [round(t, 3) for t in fr.times_ps],
                "coord_scale": fr.scale,
                "coords_b64": fr.b64(),  # int16 little-endian, shape (n_frames, n_atoms, 3)
                "aligned": fr.aligned,
            }
        )
    return data


def build_payload(
    system: System,
    selection: str = "protein",
    frame: int = 0,
    style: str = "cartoon",
    color: str = "ss",
    highlight: str | None = None,
    title: str | None = None,
    pbc: bool | None = None,
) -> dict:
    """One frame. pbc=None means: correct periodic wrapping only when a trajectory was loaded
    (structure files are shown as they are)."""
    n_frames = len(system.universe.trajectory)
    if not 0 <= frame < n_frames:
        raise ValueError(f"frame {frame} out of range 0..{n_frames - 1}")
    if pbc is None:
        pbc = bool(system.trajectories)
    notes: list[str] = []
    return _build(
        system, np.array([frame]), selection, style, color, highlight, title,
        pbc=pbc, align=False, max_payload_mb=trajectory.MAX_PAYLOAD_MB, notes=notes,
    )


def build_trajectory_payload(
    system: System,
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
    max_payload_mb: float = trajectory.MAX_PAYLOAD_MB,
) -> dict:
    """Several frames for playback: start:stop:stride thinned to max_frames, within max_payload_mb."""
    notes: list[str] = []
    indices, note = trajectory.pick_indices(len(system.universe.trajectory), start, stop, stride, max_frames)
    if note:
        notes.append(note)
    return _build(
        system, indices, selection, style, color, highlight, title,
        pbc=pbc, align=align, max_payload_mb=max_payload_mb, notes=notes,
    )
