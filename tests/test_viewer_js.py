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


def test_hydrogens_are_kept_so_frames_line_up(tmp_path):
    # ALA2-like case: topology with hydrogens; 3Dmol would drop them without keepH
    s = loader.load(D.PRMncdf, D.TRJncdf)
    p = payload.build_trajectory_payload(s, "protein", max_frames=3)
    assert s.universe.select_atoms("protein and name H*").n_atoms > 0
    out = run_harness(p, tmp_path)
    assert out["calls"]["keepH"] is True and out["ctrlOn"] is True


def test_single_frame_has_no_controls(tmp_path):
    s = loader.load(D.PDB_small)
    out = run_harness(payload.build_payload(s, "protein and name CA"), tmp_path)
    assert out["ctrlOn"] is False and out["calls"]["setFrame"] == [] and out["calls"]["setCoordinatesLen"] is None


def test_layers_labels_and_surface(tmp_path):
    s = loader.load(D.GRO, D.XTC)
    p = payload.build_trajectory_payload(
        s, "protein", max_frames=3, style="cartoon",
        layers=[{"selection": "resid 5:8", "style": "surface", "color": "chain"}],
        labels="resid 10:12", highlight="resid 20",
    )
    out = run_harness(p, tmp_path)
    assert "surface" in out["styleOptions"]
    assert out["layerRows"] == 2  # the layer and the highlight
    assert len(out["labelsAtStart"]) == 3 and out["labelsMoved"] is True
    # the layer surface is built when paused, hidden during playback and rebuilt on pause
    assert out["surfacesAtStart"] == [len(p["layer_serials"][0])]
    assert out["surfacesWhilePlaying"] == 0 and out["surfacesAfterPause"] == 1
    assert out["surfacesAfterSwitch"] == 2  # main surface + layer surface
    assert out["layerRowsAfterAdd"] == 3 and out["addedLayer"] > 0
    assert "cannot read" in out["badInputNote"]
    assert out["labelsAddedByClick"] == 1 and out["labelsAfterSecondClick"] == 0
    assert out["labelsAfterClear"] == 0 and out["themeAfterToggle"] == "dark"
    assert out["calls"]["clickableBeforeFrames"] is True
