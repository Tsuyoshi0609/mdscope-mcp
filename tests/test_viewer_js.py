"""Exercise core.js under node with stubbed DOM / 3Dmol (WebGL is not available headless)."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from MDAnalysisTests import datafiles as D

from mdscope import loader, payload

HARNESS = Path(__file__).with_name("viewer_harness.js")
CORE = Path(__file__).resolve().parents[1] / "src" / "mdscope" / "viewer" / "core.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not available")


def run_harness(p: dict, tmp_path: Path) -> dict:
    f = tmp_path / "payload.json"
    f.write_text(json.dumps(p))
    r = subprocess.run(["node", str(HARNESS), str(CORE), str(f)], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def test_trajectory_controls(tmp_path):
    s = loader.load(D.GRO, D.XTC)
    p = payload.build_trajectory_payload(s, "protein and name CA", max_frames=5)
    out = run_harness(p, tmp_path)
    assert out["ctrlOn"] is True and out["sliderMax"] == 4
    assert out["nCoords"] == 5 * p["n_atoms"] * 3 and out["calls"]["fmt"] == "array"
    first_atom = [float(x) for x in next(ln for ln in p["pdb"].splitlines() if ln.startswith("ATOM"))[30:54].split()]
    assert max(abs(a - b) for a, b in zip(out["first"], first_atom)) <= 0.006
    assert out["labelLast"].startswith(f"frame {p['frame_indices'][-1]}") and "ps" in out["labelLast"]
    assert out["labelWrap"].startswith("frame 0")
    assert out["playText"] == "▶" and len(out["calls"]["setFrame"]) >= 5  # 2 explicit + ticks at 30 fps


def test_single_frame_has_no_controls(tmp_path):
    s = loader.load(D.PDB_small)
    out = run_harness(payload.build_payload(s, "protein and name CA"), tmp_path)
    assert out["ctrlOn"] is False and out["calls"]["setFrame"] == [] and out["calls"]["setCoordinatesLen"] is None
