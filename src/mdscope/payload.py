"""Turn a System into the data the viewer HTML needs: a PDB string, optional trajectory
coordinates (int16, base64) and display settings."""

from __future__ import annotations

import os
import tempfile
import warnings
from typing import Literal, get_args

import MDAnalysis as mda
import numpy as np
from MDAnalysis.exceptions import SelectionError

from mdscope import density, trajectory
from mdscope.config import cache_dir
from mdscope.loader import LIGAND_SEL, SOLVENT_SEL
from mdscope.registry import System

Style = Literal["cartoon", "sticks", "spheres", "lines", "surface"]
Color = Literal["ss", "chain", "rainbow", "element"]
STYLES = get_args(Style)
COLORS = get_args(Color)
MAX_LABELS = 200


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


HYDROGEN_SEL = "name H* or name [0-9]H*"


def _check_layers(layers: list[dict] | None) -> list[dict]:
    out = []
    for i, ly in enumerate(layers or []):
        ly = dict(ly)
        if not ly.get("selection"):
            raise ValueError(f"layers[{i}] needs a selection")
        ly.setdefault("style", "sticks")
        ly.setdefault("color", "element")
        if ly["style"] not in STYLES or ly["color"] not in COLORS:
            raise ValueError(f"layers[{i}]: style must be one of {STYLES}, color one of {COLORS}")
        out.append({k: ly[k] for k in ("selection", "style", "color")})
    return out


def _atoms(
    system: System,
    selection: str,
    highlight: str | None,
    layers: list[dict],
    labels: str | None,
    notes: list[str],
    hydrogens: bool = True,
) -> tuple[mda.AtomGroup, dict]:
    """Atoms to embed (the selection plus any layer atoms outside it) and, per part, the 1-based
    serial numbers they get in the written PDB."""
    main = select(system, selection)
    if selection.strip() == "protein":
        # the default view should show bound ligands too
        lig = system.universe.select_atoms(LIGAND_SEL)
        if lig.n_atoms:
            main = main | lig
            notes.append(f"included {len(lig.residues)} non-protein residue(s) as ligands")
    layer_ags = [select(system, ly["selection"]) for ly in layers]
    ag = main
    for la in layer_ags:
        ag = ag | la  # a layer may add atoms outside the selection (e.g. nearby water)
    if not hydrogens:
        heavy = ag.select_atoms(f"not ({HYDROGEN_SEL})")
        if 0 < heavy.n_atoms < ag.n_atoms:
            notes.append(f"{ag.n_atoms - heavy.n_atoms} hydrogens hidden (hydrogens=True to show them)")
            ag = heavy
    # serial numbers in the written PDB are 1..N in index order (| sorts by index)
    index_of = {ix: i + 1 for i, ix in enumerate(ag.indices)}

    def serials(group: mda.AtomGroup) -> list[int]:
        return [index_of[ix] for ix in group.indices if ix in index_of]

    parts: dict = {"base_serials": None, "layer_serials": [serials(la) for la in layer_ags]}
    if ag.n_atoms > (main & ag).n_atoms:
        parts["base_serials"] = serials(main)
        notes.append(f"layers added {ag.n_atoms - (main & ag).n_atoms} atom(s) outside the selection")
    parts["highlight_serials"] = []
    if highlight:
        hl = select(system, highlight)
        inside = hl & ag
        if inside.n_atoms < hl.n_atoms:
            notes.append(f"{hl.n_atoms - inside.n_atoms} highlighted atom(s) are outside the selection and not shown")
        parts["highlight_serials"] = serials(inside)
    parts["label_serials"] = []
    if labels:
        res = (select(system, labels) & ag).residues
        if len(res) > MAX_LABELS:
            notes.append(f"labels: {len(res)} residues matched, only the first {MAX_LABELS} are labelled")
            res = res[:MAX_LABELS]
        for r in res:
            # one label per residue, on CA when there is one
            at = (r.atoms & ag).select_atoms("name CA") or (r.atoms & ag)
            parts["label_serials"].append(index_of[at[0].ix])
    return ag, parts


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
    hydrogens: bool = True,
    layers: list[dict] | None = None,
    labels: str | None = None,
) -> dict:
    if style not in STYLES:
        raise ValueError(f"style must be one of {STYLES}")
    if color not in COLORS:
        raise ValueError(f"color must be one of {COLORS}")
    u = system.universe
    layers = _check_layers(layers)
    ag, parts = _atoms(system, selection, highlight, layers, labels, notes, hydrogens)
    if len(indices) > 1 and any(w in ly["selection"] for ly in layers for w in ("around", "sphzone")):
        notes.append("distance-based layer selections are evaluated on the first frame (the atom set stays fixed)")
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
        "layers": layers,
        "labels": labels,
        **parts,
        "pbc": fr.pbc_applied,
        "shift": fr.shift,
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
    layers: list[dict] | None = None,
    labels: str | None = None,
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
        layers=layers, labels=labels,
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
    hydrogens: bool = False,
    layers: list[dict] | None = None,
    labels: str | None = None,
) -> dict:
    """Several frames for playback: start:stop:stride thinned to max_frames, within max_payload_mb.
    Hydrogens are dropped by default (they double the atom count and add little to playback)."""
    notes: list[str] = []
    indices, note = trajectory.pick_indices(len(system.universe.trajectory), start, stop, stride, max_frames)
    if note:
        notes.append(note)
    return _build(
        system, indices, selection, style, color, highlight, title,
        pbc=pbc, align=align, max_payload_mb=max_payload_mb, notes=notes, hydrogens=hydrogens,
        layers=layers, labels=labels,
    )


def build_density_payload(
    system: System,
    map_path: str,
    selection: str = "protein",
    style: str = "cartoon",
    color: str = "chain",
    highlight: str | None = None,
    title: str | None = None,
    layers: list[dict] | None = None,
    labels: str | None = None,
    level: float | None = None,
    max_voxels: int = density.MAX_VOXELS,
) -> dict:
    """One structure with a density map in the same (file) coordinates. The structure is shown
    centered, so the map is moved by the same shift."""
    data = build_payload(system, selection, 0, style, color, highlight, title, False, layers, labels)
    grid = density.read(map_path)
    if level is None:
        model = system.universe.select_atoms(f"not ({SOLVENT_SEL})")
        level, how = density.auto_level(grid.values, float(np.prod(grid.voxel)), float(model.masses.sum()))
    else:
        how = f"level {level:.3g} as requested"
    ca = select(system, selection).select_atoms("name CA")
    ag = ca if ca.n_atoms else select(system, selection)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        system.universe.trajectory[0]
    inside = density.fraction_inside(grid, ag.positions.astype(np.float64), level)
    thinned = density.thin(grid, max_voxels)
    thinned.origin = thinned.origin - np.array(data["shift"])
    name = os.path.basename(map_path)
    data["density"] = density.payload(thinned, level, name)
    data["map"] = name
    data["map_level"] = round(level, 4)
    data["atoms_inside_map"] = round(inside, 3)
    data["notes"] += thinned.notes + [how, f"{inside:.0%} of the {'CA ' if ca.n_atoms else ''}atoms lie inside the contour"]
    if inside < 0.2:
        data["notes"].append("few atoms lie inside the map: the map may be misplaced or the level too high")
    return data
