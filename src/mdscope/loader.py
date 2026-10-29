"""Build an MDAnalysis Universe from files and summarize its composition for the LLM."""

from __future__ import annotations

import warnings
from pathlib import Path

import MDAnalysis as mda

from mdscope import registry
from mdscope.config import check_path
from mdscope.registry import System

WATER = "SOL WAT HOH TIP3 TIP4 TP3 H2O"
IONS = "NA CL K MG CA ZN SOD CLA POT CAL MN FE CU NA+ CL- K+"
SOLVENT_SEL = f"resname {WATER} or resname {IONS}"
LIGAND_SEL = f"not (protein or nucleic or {SOLVENT_SEL})"

_THREE_TO_ONE = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C", "GLN": "Q", "GLU": "E",
    "GLY": "G", "HIS": "H", "ILE": "I", "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F",
    "PRO": "P", "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
    "HID": "H", "HIE": "H", "HIP": "H", "HSD": "H", "HSE": "H", "HSP": "H",
    "CYX": "C", "CYM": "C", "ASH": "D", "GLH": "E", "LYN": "K",
}


def load(topology: str, trajectory: str | list[str] | None = None, name: str | None = None) -> System:
    top = check_path(topology)
    if trajectory is None:
        trajs: list[Path] = []
    elif isinstance(trajectory, str):
        trajs = [check_path(trajectory)]
    else:
        trajs = [check_path(t) for t in trajectory]
    for p in [top, *trajs]:
        if not p.is_file():
            raise FileNotFoundError(f"{p} does not exist")

    caught: list[str] = []
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        u = mda.Universe(str(top), *[str(t) for t in trajs]) if trajs else mda.Universe(str(top))
        caught = sorted({str(x.message).splitlines()[0] for x in w})

    system = System(
        system_id=registry.make_id([top, *trajs]),
        name=name or top.stem,
        topology=top,
        trajectories=trajs,
        universe=u,
        warnings=caught,
    )
    return registry.register(system)


def _sequence(residues) -> str:
    return "".join(_THREE_TO_ONE.get(r.resname.upper(), "X") for r in residues)


def _chains(u: mda.Universe) -> list[dict]:
    protein = u.select_atoms("protein")
    chains = []
    for seg in protein.segments:
        res = seg.atoms.select_atoms("protein").residues
        if len(res) == 0:
            continue
        seq = _sequence(res)
        chains.append(
            {
                "chain": seg.segid,
                "n_residues": len(res),
                "resid_range": [int(res.resids.min()), int(res.resids.max())],
                "sequence": seq if len(seq) <= 60 else seq[:57] + "...",
            }
        )
    return chains


def _ligands(u: mda.Universe) -> list[dict]:
    lig = u.select_atoms(LIGAND_SEL)
    out = []
    for resname in sorted(set(lig.resnames)):
        g = lig.select_atoms(f"resname {resname}")
        out.append({"resname": resname, "n_copies": len(g.residues), "n_atoms_per_copy": len(g.residues[0].atoms)})
    return out


def summarize(system: System) -> dict:
    """Composition and trajectory metadata; everything the LLM needs to write a selection."""
    u = system.universe
    n_frames = len(u.trajectory)
    dt = float(u.trajectory.dt) if n_frames > 1 else None
    water = u.select_atoms(f"resname {WATER}")
    ions = u.select_atoms(f"resname {IONS}")
    box = u.dimensions
    return {
        "system_id": system.system_id,
        "name": system.name,
        "topology": str(system.topology),
        "trajectories": [str(t) for t in system.trajectories],
        "n_atoms": int(u.atoms.n_atoms),
        "n_residues": int(u.residues.n_residues),
        "has_hydrogens": bool(u.select_atoms("name H*").n_atoms),
        "n_frames": n_frames,
        "dt_ps": dt,
        "total_time_ns": round(n_frames * dt / 1000, 3) if dt else None,
        "box_A": [round(float(x), 2) for x in box[:3]] if box is not None else None,
        "chains": _chains(u),
        "ligands": _ligands(u),
        "n_water_residues": len(water.residues),
        "n_ions": int(ions.n_atoms),
        "warnings": system.warnings,
    }
