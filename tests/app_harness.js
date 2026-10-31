// Run the bridge script of app.html under node: post a tool result, answer get_view_payload
// from a file of pieces, and report which payload reached MdscopeViewer.mount.
// usage: node app_harness.js <core.js> <bridge.js> <case.json>
//   case.json: {"result": <tool result as the host delivers it>, "pieces": {"<offset>": <piece>}}
const fs = require("fs");
const [, , coreJs, bridgeJs, caseJson] = process.argv;
const C = JSON.parse(fs.readFileSync(caseJson, "utf8"));
const out = { calls: [], mounted: null, status: "" };
const els = { status: { set textContent(t) { out.status = t; } }, ctrl: { classList: { contains: () => false } },
  mapbar: { classList: { contains: () => false } },
  fullscreen: {}, viewer: {} };
let onMessage = null;
global.window = {
  addEventListener: (k, f) => { if (k === "message") onMessage = f; },
  parent: {
    postMessage(msg) {
      const reply = (result) => setTimeout(() => onMessage({ data: { jsonrpc: "2.0", id: msg.id, result } }), 0);
      if (msg.method === "ui/initialize") {
        reply({ hostContext: {} });
        setTimeout(() => onMessage({ data: { jsonrpc: "2.0", method: "ui/notifications/tool-result", params: C.result } }), 5);
      } else if (msg.method === "tools/call") {
        out.calls.push(msg.params.arguments.offset);
        reply({ structuredContent: C.pieces[String(msg.params.arguments.offset)] });
      }
    },
  },
};
global.document = { getElementById: (id) => els[id] || null };
new Function(fs.readFileSync(coreJs, "utf8"))();
window.MdscopeViewer.mount = (p) => { out.mounted = { n_atoms: p.n_atoms, pdbAtoms: (p.pdb.match(/^ATOM  /gm) || []).length,
  complete: window.MdscopeViewer.isComplete(p) }; return { resize() {}, setDark() {} }; };
global.MdscopeViewer = window.MdscopeViewer;
new Function(fs.readFileSync(bridgeJs, "utf8"))();
setTimeout(() => console.log(JSON.stringify(out)), 300);
