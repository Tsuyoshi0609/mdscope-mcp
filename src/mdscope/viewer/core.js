// Shared viewer logic for the standalone page (template.html) and the MCP App (app.html).
// Expects $3Dmol to be loaded and a DOM with #title, #meta, #style, #color, #reset, #viewer,
// #notes and the trajectory controls #ctrl (#play, #frame, #fps, #flabel).
window.MdscopeViewer = (function () {
  const HETERO = { hetflag: true, not: { resn: ["HOH", "WAT", "SOL", "TIP3"] } };

  // 3Dmol atom-style for one representation under one coloring
  function rep(style, color) {
    const c = {};
    if (color === "ss") c.colorscheme = "ssPyMOL";
    else if (color === "chain") c.colorscheme = "chain";
    else if (color === "rainbow") c.color = "spectrum";
    else c.colorscheme = "default";              // element colors
    if (style === "cartoon") return { cartoon: Object.assign({}, c) };
    if (style === "sticks")  return { stick: Object.assign({ radius: 0.2 }, c) };
    if (style === "spheres") return { sphere: Object.assign({ scale: 0.3 }, c) };
    return { line: Object.assign({}, c) };
  }

  function setTheme(dark) {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
  }

  // int16 little-endian base64 -> flat Array of Å (what 3Dmol's setCoordinates(…, "array") wants)
  function decodeCoords(b64, scale) {
    const bin = atob(b64), n = bin.length;
    const bytes = new Uint8Array(n);
    for (let i = 0; i < n; i++) bytes[i] = bin.charCodeAt(i);
    const ints = new Int16Array(bytes.buffer, 0, n >> 1);
    const out = new Array(ints.length);
    for (let i = 0; i < ints.length; i++) out[i] = ints[i] * scale;
    return out;
  }

  function fmtTime(ps) {
    if (ps >= 1000) return (ps / 1000).toFixed(ps >= 100000 ? 0 : 2) + " ns";
    return ps.toFixed(ps < 10 ? 2 : 0) + " ps";
  }

  function mount(P, opts) {
    opts = opts || {};
    const dark = opts.dark !== undefined ? opts.dark
      : !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
    setTheme(dark);
    const nFrames = P.n_frames || 1;

    document.getElementById("title").textContent = P.title;
    document.getElementById("meta").textContent =
      `${P.n_residues} residues · ${P.n_atoms} atoms · selection "${P.selection}"` +
      (nFrames > 1 ? ` · ${nFrames} of ${P.n_frames_total} frames`
        : (P.n_frames_total > 1 ? ` · frame ${P.frame}/${P.n_frames_total - 1}` : ""));
    document.getElementById("notes").textContent = (P.notes || []).join(" · ");

    const el = document.getElementById("viewer");
    el.innerHTML = "";
    let viewer;
    try {
      viewer = $3Dmol.createViewer(el, { backgroundColor: dark ? "#121212" : "#ffffff", antialias: true });
    } catch (e) { viewer = null; }
    if (!viewer) throw new Error("WebGL is not available in this browser/window, so the structure cannot be drawn");
    // keepH: 3Dmol drops hydrogens by default, which would misalign the trajectory coordinates
    const model = viewer.addModel(P.pdb, "pdb", { keepH: true });
    const nModel = model.selectedAtoms({}).length;
    if (nModel !== P.n_atoms) {
      throw new Error(`viewer parsed ${nModel} atoms but the payload has ${P.n_atoms}; coordinates would be misassigned`);
    }
    if (nFrames > 1) model.setCoordinates(decodeCoords(P.coords_b64, P.coord_scale), "array");

    const styleSel = document.getElementById("style");
    const colorSel = document.getElementById("color");
    styleSel.value = P.style;
    colorSel.value = P.color;

    function applyStyle() {
      const style = styleSel.value, color = colorSel.value;
      viewer.setStyle({}, rep(style, color));
      if (style === "cartoon") {
        // cartoon cannot draw ligands or lone residues; show them as sticks
        viewer.setStyle(HETERO, { stick: { radius: 0.25, colorscheme: "default" } });
        if (!model.selectedAtoms({ ss: ["h", "s"] }).length) {
          // no secondary structure at all (peptide, small molecule): fall back to sticks
          viewer.setStyle({}, rep("sticks", color === "ss" ? "element" : color));
        }
      }
      if (P.highlight_serials && P.highlight_serials.length) {
        viewer.addStyle({ serial: P.highlight_serials },
          { stick: { radius: 0.3, colorscheme: "magentaCarbon" } });
      }
      viewer.render();
    }

    styleSel.onchange = applyStyle;
    colorSel.onchange = applyStyle;
    document.getElementById("reset").onclick = () => { viewer.zoomTo(); viewer.render(); };
    window.addEventListener("resize", () => viewer.resize());

    // --- trajectory controls -------------------------------------------------------
    let cur = 0, playing = false, timer = null;
    const ctrl = document.getElementById("ctrl");
    const play = document.getElementById("play"), slider = document.getElementById("frame");
    const fpsSel = document.getElementById("fps"), label = document.getElementById("flabel");

    function showFrame(i, cb) {
      cur = ((i % nFrames) + nFrames) % nFrames;
      slider.value = cur;
      const t = P.times_ps ? fmtTime(P.times_ps[cur]) : "";
      label.textContent = `frame ${P.frame_indices ? P.frame_indices[cur] : cur}` + (t ? ` · ${t}` : "");
      viewer.setFrame(cur).then(() => { viewer.render(); if (cb) cb(); });
    }
    function tick() {
      if (!playing) return;
      showFrame(cur + 1, () => { timer = setTimeout(tick, 1000 / Number(fpsSel.value)); });
    }
    function setPlaying(on) {
      playing = on;
      play.textContent = on ? "❚❚" : "▶";
      clearTimeout(timer);
      if (on) tick();
    }
    if (ctrl && nFrames > 1) {
      ctrl.classList.add("on");
      slider.max = nFrames - 1;
      slider.oninput = () => { setPlaying(false); showFrame(Number(slider.value)); };
      play.onclick = () => setPlaying(!playing);
      document.addEventListener("keydown", (e) => {
        if (e.target.tagName === "SELECT" || e.target.tagName === "INPUT") return;
        if (e.key === " ") { e.preventDefault(); setPlaying(!playing); }
        else if (e.key === "ArrowRight") { setPlaying(false); showFrame(cur + 1); }
        else if (e.key === "ArrowLeft") { setPlaying(false); showFrame(cur - 1); }
      });
      showFrame(0);
    }

    applyStyle();
    viewer.zoomTo();
    viewer.render();

    return {
      viewer,
      resize: () => viewer.resize(),
      setDark: (d) => { setTheme(d); viewer.setBackgroundColor(d ? "#121212" : "#ffffff"); viewer.render(); },
      showFrame,
      setPlaying,
    };
  }

  return { mount, setTheme, decodeCoords };
})();
