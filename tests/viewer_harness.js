// Run core.js under node with a stub DOM and a stub $3Dmol to check controls, layers and labels.
// usage: node viewer_harness.js <core.js> <payload.json>   -> prints JSON with what happened
const fs = require("fs");
const [, , coreJs, payloadJson] = process.argv;
const P = JSON.parse(fs.readFileSync(payloadJson, "utf8"));

// --- minimal DOM --------------------------------------------------------------------
const calls = {
  setFrame: [], setStyle: [], addStyle: [], render: 0, setCoordinatesLen: null, keepH: null,
  surfaces: [], labels: [], clickableBeforeFrames: null,
};
function el(id, tag) {
  const classes = new Set();
  const e = {
    id, textContent: "", value: "", max: "0", style: {}, tagName: tag || (id === "frame" ? "INPUT" : "DIV"),
    children: [], options: [],
    classList: { add: (c) => classes.add(c), contains: (c) => classes.has(c) },
    addEventListener() {},
    appendChild(c) { this.children.push(c); if (c.tagName === "OPTION") this.options.push(c); return c; },
  };
  Object.defineProperty(e, "innerHTML", { set() { e.children = []; e.options = []; }, get() { return ""; } });
  return e;
}
const els = {};
["title", "meta", "style", "color", "reset", "theme", "viewer", "notes", "ctrl", "play", "frame", "fps",
  "flabel", "layers", "addsel", "addstyle", "addcolor", "add", "clearlabels"]
  .forEach((id) => (els[id] = el(id, ["style", "color", "addstyle", "addcolor"].includes(id) ? "SELECT" : undefined)));
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
  createElement: (tag) => el("", tag.toUpperCase()),
};

// --- stub 3Dmol: atoms parsed from the PDB, selections by serial / resi / chain / resn / hetflag
function parseAtoms(pdb, keepH) {
  return pdb.split("\n").filter((l) => l.startsWith("ATOM") || l.startsWith("HETATM"))
    .filter((l) => keepH || l.slice(76, 78).trim() !== "H")
    .map((l, i) => ({
      serial: i + 1, hetflag: l.startsWith("HETATM"), resn: l.slice(17, 20).trim(), chain: l.slice(21, 22),
      resi: Number(l.slice(22, 26)), x: +l.slice(30, 38), y: +l.slice(38, 46), z: +l.slice(46, 54),
    }));
}
function matches(a, sel) {
  for (const [k, v] of Object.entries(sel)) {
    if (k === "serial") { if (!(Array.isArray(v) ? v : [v]).includes(a.serial)) return false; }
    else if (k === "not") { if (matches(a, v)) return false; }
    else if (k === "ss") { /* pretend every atom is in a helix */ }
    else if (k === "resn") { if (!(Array.isArray(v) ? v : [v]).includes(a.resn)) return false; }
    else if (k === "resi" && typeof v === "string") {
      const [lo, hi] = v.split("-").map(Number); if (a.resi < lo || a.resi > hi) return false;
    } else if (a[k] !== v) return false;
  }
  return true;
}
global.$3Dmol = {
  createViewer() {
    let atoms = [], frames = null;
    stubModel = () => model;
    const model = {
      setCoordinates(arr, fmt) {
        calls.setCoordinatesLen = arr.length; calls.fmt = fmt;
        calls.clickableBeforeFrames = atoms.length > 0 && atoms.every((a) => a.clickable);
        frames = [];
        for (let f = 0; f < arr.length / (atoms.length * 3); f++) {
          frames.push(atoms.map((a, i) => Object.assign({}, a,
            { x: arr[(f * atoms.length + i) * 3], y: arr[(f * atoms.length + i) * 3 + 1], z: arr[(f * atoms.length + i) * 3 + 2] })));
        }
        atoms = frames[0];
        return frames;
      },
      selectedAtoms(sel) { return atoms.filter((a) => matches(a, sel)); },
    };
    return {
      addModel(pdb, fmt, opts) {
        calls.keepH = !!(opts && opts.keepH);
        atoms = parseAtoms(pdb, calls.keepH);
        return model;
      },
      setStyle(sel, st) { calls.setStyle.push([sel, st]); },
      addStyle(sel, st) { calls.addStyle.push([sel, st]); },
      render() { calls.render++; }, zoomTo() {},
      setFrame(i) { calls.setFrame.push(i); if (frames) atoms = frames[i]; return Promise.resolve(); },
      setClickable(sel, on, cb) { atoms.forEach((a) => { a.clickable = on; a.callback = cb; }); clickCb = cb; },
      addSurface(type, st, sel) { calls.surfaces.push({ type, st, n: model.selectedAtoms(sel).length }); },
      removeAllSurfaces() { calls.surfaces = []; },
      addLabel(text, st) { calls.labels.push({ text, x: st.position.x }); },
      removeAllLabels() { calls.labels = []; },
      resize() {}, setBackgroundColor(c) { calls.background = c; },
    };
  },
};

// --- run ------------------------------------------------------------------------------
new Function(fs.readFileSync(coreJs, "utf8"))();
let clickCb = null, stubModel = null;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  const api = window.MdscopeViewer.mount(P, { dark: false });
  const out = { ctrlOn: els.ctrl.classList.contains("on"), sliderMax: els.frame.max, meta: els.meta.textContent };
  out.styleOptions = els.style.options.map((o) => o.value);
  out.layerRows = els.layers.children.length;
  out.labelsAtStart = calls.labels.map((l) => l.text);
  await sleep(200);
  out.surfacesAtStart = calls.surfaces.map((s) => s.n);
  if (P.n_frames > 1) {
    // decode round trip: first coordinate equals first PDB atom
    const flat = window.MdscopeViewer.decodeCoords(P.coords_b64, P.coord_scale);
    out.nCoords = flat.length;
    out.first = flat.slice(0, 3);
    const x0 = calls.labels.map((l) => l.x);
    await new Promise((r) => api.showFrame(P.n_frames - 1, r));
    out.labelLast = els.flabel.textContent;
    out.labelsMoved = calls.labels.some((l, i) => l.x !== x0[i]);
    await new Promise((r) => api.showFrame(P.n_frames, r)); // wraps to 0
    out.labelWrap = els.flabel.textContent;
    // play for a few ticks at the selected fps, then pause
    els.fps.value = "30";
    api.setPlaying(true);
    await sleep(200);
    out.surfacesWhilePlaying = calls.surfaces.length;
    api.setPlaying(false);
    await sleep(200);
    out.surfacesAfterPause = calls.surfaces.length;
    out.playText = els.play.textContent;
  }
  // interactive: switch style to surface, add a layer from the text box, click an atom
  els.style.value = "surface"; els.style.onchange();
  await sleep(200);
  out.surfacesAfterSwitch = calls.surfaces.length;
  const firstResi = P.pdb.split("\n").find((l) => l.startsWith("ATOM")).slice(22, 26).trim();
  els.addsel.value = `${firstResi}-${Number(firstResi) + 2}`; els.addstyle.value = "spheres"; els.addcolor.value = "chain";
  els.add.onclick();
  out.layerRowsAfterAdd = els.layers.children.length;
  out.addedLayer = api.layers[api.layers.length - 1] && api.layers[api.layers.length - 1].sel.serial.length;
  els.addsel.value = "%%"; els.add.onclick();
  out.badInputNote = els.notes.textContent;
  // click an atom of a residue that has no label yet -> one more label; click again -> removed
  const nLabels = calls.labels.length;
  const atom = stubModel().selectedAtoms({}).find((a) => !api.labelled.has(`${a.chain}:${a.resi}`));
  clickCb(atom);
  out.labelsAddedByClick = calls.labels.length - nLabels;
  clickCb(atom);
  out.labelsAfterSecondClick = calls.labels.length - nLabels;
  els.clearlabels.onclick();
  out.labelsAfterClear = calls.labels.length;
  els.theme.onclick();
  out.themeAfterToggle = document.documentElement.dataset.theme;
  out.calls = Object.assign({}, calls, { setStyle: calls.setStyle.length, addStyle: calls.addStyle.length });
  console.log(JSON.stringify(out));
})().catch((e) => { console.log(JSON.stringify({ error: String(e && e.stack) })); process.exit(1); });
