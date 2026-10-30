// Run core.js under node with a stub DOM and a stub $3Dmol to check the trajectory controls.
// usage: node viewer_harness.js <core.js> <payload.json>   -> prints JSON with what happened
const fs = require("fs");
const [, , coreJs, payloadJson] = process.argv;
const P = JSON.parse(fs.readFileSync(payloadJson, "utf8"));

// --- minimal DOM --------------------------------------------------------------------
const calls = { setFrame: [], setStyle: 0, render: 0, setCoordinatesLen: null, errors: [], keepH: null };
function el(id) {
  const classes = new Set();
  return {
    id, textContent: "", value: "0", max: "0", innerHTML: "", style: {}, tagName: id === "frame" ? "INPUT" : "DIV",
    classList: { add: (c) => classes.add(c), contains: (c) => classes.has(c) },
    addEventListener() {},
  };
}
const els = {};
["title", "meta", "style", "color", "reset", "viewer", "notes", "ctrl", "play", "frame", "fps", "flabel"]
  .forEach((id) => (els[id] = el(id)));
els.fps.value = "10";
const listeners = {};
global.window = {
  addEventListener: (k, f) => (listeners[k] = f),
  matchMedia: () => ({ matches: false }),
  setTimeout, clearTimeout,
};
global.document = {
  documentElement: { dataset: {} },
  getElementById: (id) => els[id] || null,
  addEventListener: (k, f) => (listeners["doc:" + k] = f),
};
global.$3Dmol = {
  createViewer() {
    let nAtoms = 0;
    const model = {
      setCoordinates(arr, fmt) { calls.setCoordinatesLen = arr.length; calls.fmt = fmt; return []; },
      // {} -> all atoms (count like 3Dmol would: drop H unless keepH); {ss:...} -> pretend some helix
      selectedAtoms(sel) { return Object.keys(sel).length ? [1] : new Array(nAtoms).fill(1); },
    };
    return {
      addModel(pdb, fmt, opts) {
        calls.keepH = !!(opts && opts.keepH);
        const lines = pdb.split("\n").filter((l) => l.startsWith("ATOM") || l.startsWith("HETATM"));
        nAtoms = calls.keepH ? lines.length : lines.filter((l) => l.slice(76, 78).trim() !== "H").length;
        return model;
      },
      setStyle() { calls.setStyle++; }, addStyle() {}, render() { calls.render++; }, zoomTo() {},
      setFrame(i) { calls.setFrame.push(i); return Promise.resolve(); },
      resize() {}, setBackgroundColor() {},
    };
  },
};

// --- run ------------------------------------------------------------------------------
new Function(fs.readFileSync(coreJs, "utf8"))();
(async () => {
  const api = window.MdscopeViewer.mount(P, { dark: false });
  const out = { ctrlOn: els.ctrl.classList.contains("on"), sliderMax: els.frame.max, meta: els.meta.textContent };
  if (P.n_frames > 1) {
    // decode round trip: first coordinate equals first PDB atom
    const flat = window.MdscopeViewer.decodeCoords(P.coords_b64, P.coord_scale);
    out.nCoords = flat.length;
    out.first = flat.slice(0, 3);
    await new Promise((r) => api.showFrame(P.n_frames - 1, r));
    out.labelLast = els.flabel.textContent;
    await new Promise((r) => api.showFrame(P.n_frames, r)); // wraps to 0
    out.labelWrap = els.flabel.textContent;
    // play for a few ticks at the selected fps, then pause
    els.fps.value = "30";
    api.setPlaying(true);
    await new Promise((r) => setTimeout(r, 200));
    api.setPlaying(false);
    out.playText = els.play.textContent;
  }
  out.calls = calls;
  console.log(JSON.stringify(out));
})().catch((e) => { console.log(JSON.stringify({ error: String(e && e.stack) })); process.exit(1); });
