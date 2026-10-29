"""MCP Apps contract: ui:// resource, tool metadata, payload in _meta, app-only fetch tool."""

import asyncio
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
            p = await c.call_tool("get_view_payload", {"view_id": vid})
            assert p.data["pdb"] == r.meta[PAYLOAD_KEY]["pdb"]
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
