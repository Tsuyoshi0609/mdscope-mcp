"""MCP Apps contract: ui:// resource, tool metadata, payload in _meta, app-only fetch tool."""

import asyncio
import json
import shutil
import subprocess

import pytest
from fastmcp import Client
from MDAnalysisTests import datafiles as D

from mdscope.html import render_app_html
from mdscope.server import PAYLOAD_KEY, VIEWER_URI, mcp


def run(coro):
    return asyncio.run(coro)


def test_viewer_resource_is_mcp_app():
    async def go():
        async with Client(mcp) as c:
            res = {str(r.uri): r for r in await c.list_resources()}
            assert VIEWER_URI in res
            assert res[VIEWER_URI].mime_type == "text/html;profile=mcp-app"
            assert res[VIEWER_URI].meta["ui"]["prefersBorder"] is True
            body = (await c.read_resource(VIEWER_URI))[0]
            assert body.mime_type == "text/html;profile=mcp-app"
            assert "$3Dmol" in body.text and "MdscopeViewer" in body.text and "ui/initialize" in body.text
    run(go())


def test_view_structure_tool_links_resource():
    async def go():
        async with Client(mcp) as c:
            tools = {t.name: t for t in await c.list_tools()}
            m = tools["view_structure"].meta
            assert m["ui"]["resourceUri"] == VIEWER_URI
            assert m["openai/outputTemplate"] == VIEWER_URI
            assert tools["get_view_payload"].meta["ui"]["visibility"] == ["app"]
            for name in ("load_system", "describe_system", "mdscope_info"):
                assert "ui" not in (tools[name].meta or {})
    run(go())


def test_payload_in_meta_and_fetchable(tmp_path, monkeypatch):
    monkeypatch.setenv("MDSCOPE_CACHE_DIR", str(tmp_path))

    async def go():
        async with Client(mcp) as c:
            r = await c.call_tool("view_structure", {"topology": str(D.PDB_small)})
            s = r.structured_content
            assert "pdb" not in str(s)  # model-visible part carries no coordinates
            assert "\nATOM" in r.meta[PAYLOAD_KEY]["pdb"]
            assert r.meta[PAYLOAD_KEY]["n_atoms"] == s["summary"]["n_atoms"]
            vid = s["summary"]["view_id"]
            text, offset = "", 0
            while True:
                part = (await c.call_tool("get_view_payload", {"view_id": vid, "offset": offset})).data
                assert len(part["data"]) <= 24000
                text += part["data"]
                offset += len(part["data"])
                if offset >= part["total"]:
                    break
            assert json.loads(text)["pdb"] == r.meta[PAYLOAD_KEY]["pdb"]
            with pytest.raises(Exception, match="no view"):
                await c.call_tool("get_view_payload", {"view_id": "0000000000"})
    run(go())


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_app_html_scripts_parse(tmp_path):
    import re

    html = render_app_html()
    for i, js in enumerate(re.findall(r"<script>(.*?)</script>", html, re.DOTALL)):
        f = tmp_path / f"s{i}.js"
        f.write_text(js)
        subprocess.run(["node", "--check", str(f)], check=True)


def _codex_cut(result: dict, keep: int = 32000) -> dict:
    """What Codex hands the app for a long result: both ends of the JSON text kept, the middle
    replaced by a marker. The cut falls inside string values, so the text still parses."""
    text = json.dumps(result)
    cut = text[:keep] + f"…{len(text) - 2 * keep} chars truncated…" + text[-keep:]
    return json.loads(cut)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_app_refetches_a_payload_cut_short(tmp_path, monkeypatch):
    import re
    from pathlib import Path

    monkeypatch.setenv("MDSCOPE_CACHE_DIR", str(tmp_path))

    async def go():
        async with Client(mcp) as c:
            r = await c.call_tool("view_trajectory", {"topology": str(D.GRO), "trajectory": str(D.XTC)})
            result = {"structuredContent": r.structured_content, "_meta": r.meta}
            pieces, offset, total = {}, 0, 1
            while offset < total:
                part = (await c.call_tool("get_view_payload", {"view_id": r.structured_content["summary"]["view_id"],
                                                               "offset": offset})).data
                pieces[str(offset)] = part
                offset += len(part["data"])
                total = part["total"]
            return result, pieces, r.meta[PAYLOAD_KEY]["n_atoms"]

    result, pieces, n_atoms = run(go())
    bridge = re.findall(r"<script>(.*?)</script>", render_app_html(), re.DOTALL)[-1]
    core = Path(__file__).resolve().parents[1] / "src" / "mdscope" / "viewer" / "core.js"
    (tmp_path / "bridge.js").write_text(bridge)
    for cut, expect_calls in ((False, 0), (True, len(pieces))):
        case = tmp_path / "case.json"
        case.write_text(json.dumps({"result": _codex_cut(result) if cut else result, "pieces": pieces}))
        out = subprocess.run(
            ["node", str(Path(__file__).with_name("app_harness.js")), str(core), str(tmp_path / "bridge.js"), str(case)],
            capture_output=True, text=True, check=True,
        )
        o = json.loads(out.stdout)
        assert o["mounted"] == {"n_atoms": n_atoms, "pdbAtoms": n_atoms, "complete": True}, o
        assert len(o["calls"]) == expect_calls
