import asyncio
import json
import re

import pytest
from fastmcp import Client
from MDAnalysisTests import datafiles as D

from mdscope import loader, payload
from mdscope.html import write_html
from mdscope.server import mcp


def test_payload_protein_only_pdb():
    s = loader.load(D.GRO, D.XTC)
    p = payload.build_payload(s, "protein", frame=3)
    assert p["n_atoms"] == s.universe.select_atoms("protein").n_atoms
    assert p["pdb"].count("\nATOM") + p["pdb"].startswith("ATOM") >= p["n_atoms"]
    assert p["frame"] == 3


def test_payload_highlight_serials_are_within_selection():
    s = loader.load(D.PDB_small)
    p = payload.build_payload(s, "protein", highlight="resid 10:12 and name CA")
    assert len(p["highlight_serials"]) == 3
    assert max(p["highlight_serials"]) <= p["n_atoms"]


def test_payload_bad_selection_has_hint():
    s = loader.load(D.PDB_small)
    with pytest.raises(ValueError, match="Examples"):
        payload.build_payload(s, "protien")
    with pytest.raises(ValueError, match="no atoms"):
        payload.build_payload(s, "resname XYZ")


def test_write_html_embeds_payload_and_lib(tmp_path):
    s = loader.load(D.PDB_small)
    p = payload.build_payload(s, "protein")
    out = write_html(p, tmp_path)
    html = out.read_text()
    assert "$3Dmol" in html and "__PAYLOAD_JSON__" not in html
    m = re.search(r'<script type="application/json" id="payload">(.*?)</script>', html, re.DOTALL)
    assert json.loads(m.group(1))["n_atoms"] == p["n_atoms"]
    assert out.stat().st_size < 8e6
    assert write_html(p, tmp_path) == out  # cached


def test_view_structure_tool_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("MDSCOPE_CACHE_DIR", str(tmp_path))

    async def go():
        async with Client(mcp) as c:
            r = await c.call_tool("view_structure", {"topology": str(D.PDB_small), "color": "chain"})
            return r.structured_content

    data = asyncio.run(go())
    assert data["artifacts"][0]["path"].endswith(".html")
    assert data["summary"]["color"] == "chain"


def test_view_tools_advertise_enums_and_read_only():
    from typing import get_args

    from mdscope.server import Color, Style

    assert get_args(Style) == payload.STYLES and get_args(Color) == payload.COLORS

    async def go():
        async with Client(mcp) as c:
            return {t.name: t for t in await c.list_tools()}

    tools = asyncio.run(go())
    props = tools["view_trajectory"].inputSchema["properties"]
    assert props["style"]["enum"] == list(payload.STYLES)
    assert all(t.annotations.read_only_hint for n, t in tools.items() if n != "get_view_payload")
