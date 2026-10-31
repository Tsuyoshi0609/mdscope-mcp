"""Density maps: header conventions place the map on the model, thinning, viewer isosurface."""

import json
import shutil
import subprocess
from pathlib import Path

import mrcfile
import numpy as np
import pytest
from MDAnalysisTests import datafiles as D

from mdscope import density, loader, payload

VIEWER = Path(__file__).resolve().parents[1] / "src" / "mdscope" / "viewer"


@pytest.fixture(autouse=True)
def allow_tmp(tmp_path, monkeypatch):
    # maps are written to tmp_path, outside the default allowed root ($HOME)
    monkeypatch.setenv("MDSCOPE_ALLOWED_ROOTS", f"{Path.home()}:{tmp_path}")


def blob_map(path: Path, xyz: np.ndarray, voxel: float = 1.5, axes=(1, 2, 3), use_origin: bool = False):
    """Write a map with a Gaussian on every atom. axes = (mapc, mapr, maps); the box is placed
    either with nxstart/nystart/nzstart or with the origin record."""
    lo = np.floor(xyz.min(0) / voxel).astype(int) - 4
    n = (np.ceil(xyz.max(0) / voxel).astype(int) + 4) - lo + 1
    grid = np.stack(np.meshgrid(*[(lo[i] + np.arange(n[i])) * voxel for i in range(3)], indexing="ij"), -1)
    vals = np.zeros(n, dtype=np.float32)
    for a in xyz[:: max(1, len(xyz) // 400)]:
        vals += np.exp(-np.sum((grid - a) ** 2, axis=-1) / (2 * 1.5**2))
    # file array is (section, row, column) = axes (maps, mapr, mapc)
    file_axes = [axes[2] - 1, axes[1] - 1, axes[0] - 1]
    data = np.ascontiguousarray(np.transpose(vals, file_axes))
    with mrcfile.new(str(path), overwrite=True) as m:
        m.set_data(data)
        m.voxel_size = voxel
        m.header.mapc, m.header.mapr, m.header.maps = axes
        m.header.mx, m.header.my, m.header.mz = n  # sampling along x, y, z
        m.header.cella = tuple(n * voxel)
        start = [lo[axes[0] - 1], lo[axes[1] - 1], lo[axes[2] - 1]]
        if use_origin:
            m.header.origin = tuple(lo * voxel)
        else:
            m.header.nxstart, m.header.nystart, m.header.nzstart = start
    return path


@pytest.mark.parametrize("axes,use_origin", [((1, 2, 3), False), ((3, 2, 1), False), ((2, 3, 1), True)])
def test_map_lands_on_the_model(tmp_path, axes, use_origin):
    s = loader.load(D.PDB_small)
    ca = s.universe.select_atoms("name CA").positions.astype(float)
    m = blob_map(tmp_path / "m.mrc", s.universe.select_atoms("protein").positions.astype(float),
                 axes=axes, use_origin=use_origin)
    g = density.read(str(m))
    assert density.fraction_inside(g, ca, 0.3) > 0.9
    assert density.fraction_inside(g, ca + 15.0, 0.3) < 0.5  # a shifted model would be caught
    p = payload.build_density_payload(s, str(m))
    assert p["atoms_inside_map"] > 0.9


def test_thin_keeps_the_center(tmp_path):
    s = loader.load(D.PDB_small)
    m = blob_map(tmp_path / "m.mrc", s.universe.select_atoms("protein").positions.astype(float), voxel=1.0)
    g = density.read(str(m))
    t = density.thin(g, max_voxels=max(g.values.shape) // 3)
    assert max(t.values.shape) <= max(g.values.shape) // 3
    center = lambda grid: grid.origin + (np.array(grid.values.shape) - 1) / 2 * grid.voxel
    f = round(t.voxel[0] / g.voxel[0])
    full = np.array(g.values.shape) // f * f  # thinning drops the last partial block
    assert f >= 3 and np.allclose(center(t), g.origin + (full - 1) / 2 * g.voxel)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_viewer_isosurface_matches_the_shown_model(tmp_path):
    s = loader.load(D.PDB_small)
    m = blob_map(tmp_path / "m.mrc", s.universe.select_atoms("protein").positions.astype(float), axes=(3, 1, 2))
    p = payload.build_density_payload(s, str(m), selection="protein", max_voxels=40)
    f = tmp_path / "p.json"
    f.write_text(json.dumps(p))
    r = subprocess.run(["node", str(Path(__file__).with_name("density_check.js")), str(VIEWER / "3Dmol-min.js"),
                        str(VIEWER / "core.js"), str(f)], capture_output=True, text=True, check=True)
    iso = json.loads(r.stdout)
    shown = np.array([[float(ln[30:38]), float(ln[38:46]), float(ln[46:54])]
                      for ln in p["pdb"].splitlines() if ln.startswith(("ATOM", "HETATM"))])
    assert iso["n"] > 100
    # the contour wraps the shown (centered) atoms: boxes agree within a few Å
    assert np.abs(np.array(iso["lo"]) - shown.min(0)).max() < 6
    assert np.abs(np.array(iso["hi"]) - shown.max(0)).max() < 6
