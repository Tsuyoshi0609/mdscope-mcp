"""Pick frames from a trajectory and turn them into compact viewer coordinates.

Pipeline per frame (all in numpy, no bond information needed):
  make residues whole -> make the chain contiguous (minimum image between consecutive
  residue centers) -> move the selection's centroid to the origin -> (optionally) align
  on CA atoms to the first frame -> quantize to int16 (0.01 Å unless the system is too big).
"""

from __future__ import annotations

import base64
import warnings
from dataclasses import dataclass, field

import MDAnalysis as mda
import numpy as np
from MDAnalysis.analysis.align import rotation_matrix
from MDAnalysis.lib.distances import minimize_vectors

MAX_PAYLOAD_MB = 8.0  # keep well under the 16 MB Artifact limit; base64 adds 1/3
MIN_SCALE = 0.01  # Å per int16 unit


@dataclass
class Frames:
    indices: list[int]  # original frame numbers
    times_ps: list[float]
    coords: np.ndarray  # float32 (k, n_atoms, 3), processed
    scale: float  # Å per int16 unit
    pbc_applied: bool
    aligned: bool
    notes: list[str] = field(default_factory=list)

    @property
    def n_frames(self) -> int:
        return len(self.indices)

    def int16(self) -> np.ndarray:
        return np.round(self.coords / self.scale).astype("<i2")

    def b64(self) -> str:
        return base64.b64encode(self.int16().tobytes()).decode("ascii")

    def payload_mb(self) -> float:
        return self.coords.size * 2 * 4 / 3 / 1e6


def pick_indices(
    n_total: int, start: int = 0, stop: int | None = None, stride: int | None = None, max_frames: int = 50
) -> tuple[np.ndarray, str | None]:
    """Frame numbers to show: start:stop:stride, thinned evenly to at most max_frames."""
    stop = n_total if stop is None else stop
    if not 0 <= start < n_total:
        raise ValueError(f"start {start} out of range 0..{n_total - 1}")
    if not start < stop <= n_total:
        raise ValueError(f"stop {stop} must be in {start + 1}..{n_total}")
    if stride is not None and stride < 1:
        raise ValueError("stride must be >= 1")
    if max_frames < 1:
        raise ValueError("max_frames must be >= 1")
    idx = np.arange(start, stop, stride or 1)
    note = None
    if len(idx) > max_frames:
        idx = idx[np.unique(np.linspace(0, len(idx) - 1, max_frames).round().astype(int))]
        note = f"showing {len(idx)} of {stop - start} frames (every {idx[1] - idx[0]} frames)" if len(idx) > 1 else None
    return idx, note


def _valid_box(dim) -> np.ndarray | None:
    if dim is None:
        return None
    box = np.asarray(dim, dtype=np.float32)
    return box if box.shape == (6,) and np.all(box[:3] > 0) else None


def make_whole(xyz: np.ndarray, res_inverse: np.ndarray, res_first: np.ndarray, box: np.ndarray) -> np.ndarray:
    """Undo periodic wrapping without bonds: each residue around its first atom, then each
    residue next to the previous one (minimum image of residue centers)."""
    xyz = xyz.astype(np.float64)
    ref = xyz[res_first][res_inverse]
    xyz = ref + minimize_vectors(xyz - ref, box)
    n_res = len(res_first)
    if n_res > 1:
        centers = np.zeros((n_res, 3))
        np.add.at(centers, res_inverse, xyz)
        centers /= np.bincount(res_inverse, minlength=n_res)[:, None]
        dc = centers[1:] - centers[:-1]
        shift = np.vstack([np.zeros(3), np.cumsum(minimize_vectors(dc, box) - dc, axis=0)])
        xyz += shift[res_inverse]
    return xyz


def extract(
    u: mda.Universe,
    ag: mda.AtomGroup,
    indices: np.ndarray,
    pbc: bool = True,
    align: bool = True,
    max_payload_mb: float = MAX_PAYLOAD_MB,
) -> Frames:
    notes: list[str] = []
    n_atoms = ag.n_atoms
    budget_frames = int(max_payload_mb * 1e6 * 3 / 4 // (n_atoms * 6))
    if budget_frames < 1:
        raise ValueError(
            f"{n_atoms} atoms do not fit one frame in {max_payload_mb} MB; narrow the selection "
            f"(e.g. 'protein and not name H*', 'name CA') or raise max_payload_mb"
        )
    if len(indices) > budget_frames:
        indices = indices[np.unique(np.linspace(0, len(indices) - 1, budget_frames).round().astype(int))]
        notes.append(f"reduced to {len(indices)} frames to stay under {max_payload_mb} MB; narrow the selection for more")

    # residue bookkeeping for make_whole (selection order; residues need not be contiguous)
    _, res_first, res_inverse = np.unique(ag.resindices, return_index=True, return_inverse=True)
    ca = np.flatnonzero(ag.names == "CA") if hasattr(ag, "names") else np.array([], dtype=int)
    fit = ca if len(ca) >= 3 else np.arange(n_atoms)

    coords = np.empty((len(indices), n_atoms, 3), dtype=np.float32)
    times: list[float] = []
    pbc_applied = False
    for k, ts in enumerate(u.trajectory[[int(i) for i in indices]]):
        xyz = ag.positions.astype(np.float64)
        box = _valid_box(ts.dimensions) if pbc else None
        if box is not None:
            xyz = make_whole(xyz, res_inverse, res_first, box)
            pbc_applied = True
        xyz -= xyz.mean(axis=0)
        coords[k] = xyz
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # "Reader has no dt information" for single structures
            times.append(float(ts.time) if ts.time is not None else float(ts.frame))

    if pbc and not pbc_applied:
        notes.append("no box information; periodic-boundary correction skipped")
    if len(times) > 1 and not np.all(np.diff(times) > 0):
        # concatenated files often restart the clock; frame number × dt is at least monotonic
        dt = float(getattr(u.trajectory, "dt", 1.0) or 1.0)
        times = [float(i) * dt for i in indices]
        notes.append(f"time stamps in the file are not monotonic; showing frame × {dt:g} ps")

    aligned = False
    if align and len(indices) > 1:
        ref = coords[0, fit].astype(np.float64)
        ref_c = ref.mean(axis=0)
        for k in range(1, len(indices)):
            mob = coords[k, fit].astype(np.float64)
            mob_c = mob.mean(axis=0)
            rot, _ = rotation_matrix(mob - mob_c, ref - ref_c)
            coords[k] = (coords[k].astype(np.float64) - mob_c) @ rot.T + ref_c
        aligned = True
        notes.append(f"frames aligned on {'CA atoms' if fit is ca else 'all atoms'} of the first frame")

    max_abs = float(np.abs(coords).max()) if coords.size else 0.0
    scale = max(MIN_SCALE, max_abs / 32000.0)
    if scale > MIN_SCALE:
        notes.append(f"coordinates quantized to {scale:.3f} Å (system wider than 320 Å)")

    return Frames(
        indices=[int(i) for i in indices],
        times_ps=times,
        coords=coords,
        scale=scale,
        pbc_applied=pbc_applied,
        aligned=aligned,
        notes=notes,
    )
