"""Trajectory payloads: frame picking, periodic-boundary repair, int16 round trip, tool result."""

import asyncio
import base64

import numpy as np
import pytest
from fastmcp import Client
from MDAnalysisTests import datafiles as D

from mdscope import loader, payload, trajectory
from mdscope.server import PAYLOAD_KEY, mcp


def decode(p):
    a = np.frombuffer(base64.b64decode(p["coords_b64"]), dtype="<i2")
    return a.reshape(p["n_frames"], p["n_atoms"], 3) * p["coord_scale"]


def test_pick_indices_thins_evenly():
    idx, note = trajectory.pick_indices(1000, max_frames=10)
    assert len(idx) == 10 and idx[0] == 0 and idx[-1] == 999 and "every 111" in note
    idx, note = trajectory.pick_indices(1000, start=10, stop=20)
    assert list(idx) == list(range(10, 20)) and note is None
    idx, _ = trajectory.pick_indices(1000, stride=100, max_frames=50)
    assert list(idx) == list(range(0, 1000, 100))
    with pytest.raises(ValueError, match="stop"):
        trajectory.pick_indices(10, start=5, stop=3)


def test_gro_xtc_frames_are_whole_and_roundtrip():
    s = loader.load(D.GRO, D.XTC)
    p = payload.build_trajectory_payload(s, "protein", max_frames=50)
    assert p["n_frames"] == len(s.universe.trajectory) == 10
    assert p["pbc"] is True and p["aligned"] is True
    xyz = decode(p)
    # frame 0 in the PDB text equals the decoded first frame to int16 precision
    lines = [ln for ln in p["pdb"].splitlines() if ln.startswith(("ATOM", "HETATM"))]
    pdb0 = np.array([[float(ln[30:38]), float(ln[38:46]), float(ln[46:54])] for ln in lines])
    assert np.abs(pdb0 - xyz[0]).max() <= 0.006
    # the raw frames are broken across the box (CA-CA > 70 Å); repaired ones are not
    ca = np.array([ln[12:16].strip() == "CA" for ln in lines])
    for k in range(p["n_frames"]):
        assert np.linalg.norm(np.diff(xyz[k][ca], axis=0), axis=1).max() < 4.5
    # centered: centroid at the origin
    assert np.abs(xyz.mean(axis=1)).max() < 1.0
    assert p["times_ps"][1] - p["times_ps"][0] == pytest.approx(100.0)


def test_make_whole_repairs_a_wrapped_chain():
    box = np.array([20.0, 20.0, 20.0, 90.0, 90.0, 90.0], dtype=np.float32)
    # 3 residues of 2 atoms along x, 1.5 Å apart; residue 2 wrapped by -20, atom 5 wrapped by +20
    xyz = np.array([[0, 0, 0], [1.5, 0, 0], [3, 0, 0], [4.5, 0, 0], [6 - 20, 0, 0], [7.5, 0, 0]], float)
    res = np.array([0, 0, 1, 1, 2, 2])
    out = trajectory.make_whole(xyz, res, np.array([0, 2, 4]), box)
    assert np.allclose(np.diff(out[:, 0]), 1.5)


def test_amber_netcdf_and_budget():
    s = loader.load(D.PRMncdf, D.TRJncdf)
    p = payload.build_trajectory_payload(s, "protein", max_frames=10, max_payload_mb=0.002)
    assert 1 < p["n_frames"] < 10 and any("reduced" in n for n in p["notes"])
    with pytest.raises(ValueError, match="narrow the selection"):
        payload.build_trajectory_payload(s, "all", max_payload_mb=0.002)


def test_single_frame_has_no_coords_and_pbc_auto():
    s = loader.load(D.GRO, D.XTC)
    p = payload.build_payload(s, "protein", frame=2)
    assert "coords_b64" not in p and p["pbc"] is True and p["frame"] == 2
    s2 = loader.load(D.PDB_small)
    assert payload.build_payload(s2, "protein")["pbc"] is False


def test_view_trajectory_tool(tmp_path, monkeypatch):
    monkeypatch.setenv("MDSCOPE_CACHE_DIR", str(tmp_path))

    async def go():
        async with Client(mcp) as c:
            tools = {t.name: t for t in await c.list_tools()}
            assert tools["view_trajectory"].meta["ui"]["resourceUri"] == tools["view_structure"].meta["ui"]["resourceUri"]
            r = await c.call_tool(
                "view_trajectory", {"topology": str(D.GRO), "trajectory": str(D.XTC), "max_frames": 4}
            )
            return r

    r = asyncio.run(go())
    s = r.structured_content["summary"]
    assert s["n_frames"] == 4 and s["time_span_ps"] == [0.0, 900.0]
    assert "coords_b64" not in str(r.structured_content) and "pdb" not in str(r.structured_content)
    assert r.meta[PAYLOAD_KEY]["n_frames"] == 4
    from pathlib import Path

    html = Path(r.structured_content["artifacts"][0]["path"]).read_text()
    assert "coords_b64" in html and 'id="ctrl"' in html
