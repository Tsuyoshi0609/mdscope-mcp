"""Read a density map (.mrc / .map / .ccp4) into values[x, y, z] placed in Å, thin it to a voxel
budget and quantize it to uint8 for the viewer's isosurface."""

from __future__ import annotations

import base64
import warnings
from dataclasses import dataclass

import mrcfile
import numpy as np

from mdscope.config import check_path

MAX_VOXELS = 128  # per axis after thinning; 128³ uint8 is 2.1 MB (2.8 MB as base64)
DA_VOLUME = 1.21  # Å³ per dalton of protein, for the automatic contour level


@dataclass
class Grid:
    values: np.ndarray  # float32 (nx, ny, nz), index x slowest
    origin: np.ndarray  # Å, center of voxel (0, 0, 0)
    voxel: np.ndarray  # Å per voxel along x, y, z
    notes: list[str]


def read(path: str) -> Grid:
    """The map as values[x, y, z] with the Å position of the first voxel (MRC2014 header)."""
    p = check_path(path)
    if not p.is_file():
        raise FileNotFoundError(f"{p} does not exist")
    notes: list[str] = []
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        with mrcfile.open(str(p), permissive=True) as m:
            if m.data is None:
                raise ValueError(f"{p} could not be read as an MRC/CCP4 map")
            h = m.header
            data = np.asarray(m.data, dtype=np.float32)
            angles = [float(h.cellb.alpha), float(h.cellb.beta), float(h.cellb.gamma)]
            cell = np.array([float(h.cella.x), float(h.cella.y), float(h.cella.z)])
            sampling = np.array([int(h.mx), int(h.my), int(h.mz)])
            axes = [int(h.mapc), int(h.mapr), int(h.maps)]  # file column / row / section -> x=1, y=2, z=3
            start_crs = [int(h.nxstart), int(h.nystart), int(h.nzstart)]
            origin_hdr = np.array([float(h.origin.x), float(h.origin.y), float(h.origin.z)])
    # header problems come as RuntimeWarning (permissive=True); numpy deprecations are noise
    notes += sorted({str(x.message).splitlines()[0] for x in w if issubclass(x.category, RuntimeWarning)})
    if data.ndim != 3:
        raise ValueError(f"{p.name} has {data.ndim} dimensions; only 3D maps are supported")
    if any(abs(a - 90.0) > 0.01 for a in angles):
        raise ValueError(f"{p.name} has a non-orthogonal cell {angles}; not supported")
    if sorted(axes) != [1, 2, 3]:
        raise ValueError(f"{p.name} has an invalid axis order mapc/mapr/maps={axes}")

    # numpy order is (section, row, column); put the x axis first, then y, then z
    file_axes = [axes[2] - 1, axes[1] - 1, axes[0] - 1]
    values = np.ascontiguousarray(np.transpose(data, np.argsort(file_axes)))
    voxel = cell / np.where(sampling > 0, sampling, 1)
    start = np.zeros(3)
    for crs, ax in enumerate(axes):
        start[ax - 1] = start_crs[crs]
    # MRC2014: a non-zero origin record wins; older files place the box with n*start
    origin = origin_hdr if np.any(origin_hdr != 0) else start * voxel
    return Grid(values=values, origin=origin, voxel=voxel, notes=notes)


def thin(g: Grid, max_voxels: int = MAX_VOXELS) -> Grid:
    """Average f×f×f blocks so that every axis has at most max_voxels voxels."""
    f = int(np.ceil(max(g.values.shape) / max_voxels))
    if f <= 1:
        return g
    nx, ny, nz = (s // f for s in g.values.shape)
    v = g.values[: nx * f, : ny * f, : nz * f].reshape(nx, f, ny, f, nz, f).mean(axis=(1, 3, 5))
    notes = g.notes + [f"map averaged in {f}×{f}×{f} blocks to {nx}×{ny}×{nz} voxels (max_voxels={max_voxels})"]
    # a block's value sits at the center of the voxels it averages
    return Grid(values=v.astype(np.float32), origin=g.origin + (f - 1) / 2 * g.voxel, voxel=g.voxel * f, notes=notes)


def auto_level(values: np.ndarray, voxel_volume: float, mass_da: float | None) -> tuple[float, str]:
    """Contour level enclosing the volume of the model's mass, or mean + 2σ without a model."""
    if mass_da:
        n = round(mass_da * DA_VOLUME / voxel_volume)
        if 0 < n < values.size:
            level = float(np.partition(values.ravel(), values.size - n)[values.size - n])
            return level, f"level {level:.3g} encloses {mass_da / 1000:.0f} kDa × {DA_VOLUME} Å³/Da"
    level = float(values.mean() + 2 * values.std())
    return level, f"level {level:.3g} = mean + 2σ"


def fraction_inside(g: Grid, xyz: np.ndarray, level: float) -> float:
    """Share of the positions whose nearest voxel is above level (outside the box counts as below).
    A model fitted into the map gives most atoms inside; a misplaced map gives almost none."""
    ijk = np.round((xyz - g.origin) / g.voxel).astype(int)
    ok = np.all((ijk >= 0) & (ijk < np.array(g.values.shape)), axis=1)
    inside = np.zeros(len(xyz), dtype=bool)
    inside[ok] = g.values[ijk[ok, 0], ijk[ok, 1], ijk[ok, 2]] > level
    return float(inside.mean()) if len(xyz) else 0.0


def payload(g: Grid, level: float, name: str) -> dict:
    """Viewer data: uint8 grid (value = vmin + q * step), x slowest, as base64."""
    v = g.values
    lo, hi = float(v.min()), float(v.max())
    step = (hi - lo) / 255 or 1.0
    q = np.round((v - lo) / step).clip(0, 255).astype(np.uint8)
    return {
        "name": name,
        "size": [int(s) for s in v.shape],
        "origin": [float(x) for x in g.origin],
        "unit": [float(x) for x in g.voxel],
        "vmin": lo,
        "step": step,
        "level": level,
        # slider range: from the median (mostly solvent) to the maximum
        "range": [float(np.median(v)), hi],
        "data_b64": base64.b64encode(q.tobytes()).decode("ascii"),
    }
