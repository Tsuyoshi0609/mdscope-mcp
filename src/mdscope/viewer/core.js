// Shared viewer logic for the standalone page (template.html) and the MCP App (app.html).
// Expects $3Dmol to be loaded and a DOM with #title, #meta, #style, #color, #reset, #theme,
// #viewer, #notes, the layer panel (#layers, #addsel, #addstyle, #addcolor, #add, #clearlabels)
// and the trajectory controls #ctrl (#play, #frame, #fps, #flabel). Missing elements are skipped.
window.MdscopeViewer = (function () {
  const SOLVENT = ["HOH", "WAT", "SOL", "TIP3"];
  const STYLES = ["cartoon", "sticks", "spheres", "lines", "surface"];
  const COLORS = { ss: "secondary structure", chain: "chain", rainbow: "rainbow (N→C)",
    element: "element", magenta: "magenta" };
  const $ = (id) => document.getElementById(id);

  // 3Dmol coloring for one scheme; resi range is needed for rainbow surfaces
  function colorSpec(color, range) {
    if (color === "ss") return { colorscheme: "ssPyMOL" };
    if (color === "chain") return { colorscheme: "chain" };
    if (color === "magenta") return { colorscheme: "magentaCarbon" };
    if (color === "rainbow") {
      return range ? { colorscheme: { prop: "resi", gradient: "roygb", min: range[0], max: range[1] } }
        : { color: "spectrum" };
    }
    return { colorscheme: "default" };               // element colors
  }

  // 3Dmol atom-style for one representation (surface = cartoon underneath; the mesh is separate)
  function rep(style, color) {
    const c = colorSpec(color);
    if (style === "cartoon" || style === "surface") return { cartoon: c };
    if (style === "sticks") return { stick: Object.assign({ radius: 0.2 }, c) };
    if (style === "spheres") return { sphere: Object.assign({ scale: 0.3 }, c) };
    return { line: c };
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

  // "10-20, 45, A:30-40, LIG" -> serials of matching atoms (residue numbers, chain:range, resname)
  function parseResidues(model, text) {
    const out = new Set();
    for (const tok of text.split(/[\s,]+/).filter(Boolean)) {
      const m = tok.match(/^(?:([A-Za-z0-9]):)?(-?\d+)(?:-(-?\d+))?$/);
      let sel;
      if (m) {
        sel = { resi: m[3] !== undefined ? `${m[2]}-${m[3]}` : Number(m[2]) };
        if (m[1]) sel.chain = m[1];
      } else if (/^[A-Za-z0-9]{1,4}$/.test(tok)) {
        sel = { resn: tok.toUpperCase() };
      } else {
        throw new Error(`cannot read "${tok}"; use residue numbers (10-20), chain:range (A:10-20) or a residue name`);
      }
      model.selectedAtoms(sel).forEach((a) => out.add(a.serial));
    }
    if (!out.size) throw new Error(`"${text}" matched no atoms`);
    return [...out];
  }

  function option(sel, value, text) {
    const o = document.createElement("option");
    o.value = value; o.textContent = text;
    sel.appendChild(o);
  }
  function fillSelect(sel, values, current) {
    if (!sel) return;
    if (!sel.options || !sel.options.length) values.forEach(([v, t]) => option(sel, v, t));
    sel.value = current;
  }

  function mount(P, opts) {
    opts = opts || {};
    let dark = opts.dark !== undefined && opts.dark !== null ? opts.dark
      : !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
    setTheme(dark);
    const nFrames = P.n_frames || 1;

    $("title").textContent = P.title;
    $("meta").textContent =
      `${P.n_residues} residues · ${P.n_atoms} atoms · selection "${P.selection}"` +
      (nFrames > 1 ? ` · ${nFrames} of ${P.n_frames_total} frames`
        : (P.n_frames_total > 1 ? ` · frame ${P.frame}/${P.n_frames_total - 1}` : ""));
    const notesEl = $("notes");
    const baseNotes = (P.notes || []).join(" · ");
    notesEl.textContent = baseNotes;
    const flash = (t) => { notesEl.textContent = t; setTimeout(() => { notesEl.textContent = baseNotes; }, 4000); };

    const el = $("viewer");
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
    // click an atom: toggle a label on its residue. Set before setCoordinates, which copies
    // the atoms into every frame (setClickable only touches the current frame's atoms)
    viewer.setClickable({}, true, (atom) => toggleLabel(atom));
    if (nFrames > 1) model.setCoordinates(decodeCoords(P.coords_b64, P.coord_scale), "array");

    // --- what to draw: the main selection plus layers -----------------------------
    const baseSel = P.base_serials ? { serial: P.base_serials } : {};
    const baseSet = P.base_serials ? new Set(P.base_serials) : null;
    const inBase = (a) => !baseSet || baseSet.has(a.serial);
    // cartoon cannot draw ligands or lone residues; those are shown as sticks
    const hetSerials = model.selectedAtoms({ hetflag: true, not: { resn: SOLVENT } })
      .filter(inBase).map((a) => a.serial);
    const hasSS = model.selectedAtoms({ ss: ["h", "s"] }).some(inBase);
    const resis = model.selectedAtoms({}).map((a) => a.resi);
    const resiRange = [Math.min(...resis), Math.max(...resis)];

    const layers = (P.layers || []).map((ly, i) => ({
      name: ly.selection, style: ly.style, color: ly.color, visible: true,
      sel: { serial: (P.layer_serials || [])[i] || [] },
    }));
    if (P.highlight_serials && P.highlight_serials.length) {
      layers.push({ name: `highlight: ${P.highlight}`, style: "sticks", color: "magenta", visible: true,
        sel: { serial: P.highlight_serials } });
    }
    const labelled = new Map();   // "chain:resi" -> serial the label sits on
    (P.label_serials || []).forEach((s) => {
      const a = model.selectedAtoms({ serial: s })[0];
      if (a) labelled.set(`${a.chain}:${a.resi}`, s);
    });

    const styleSel = $("style"), colorSel = $("color");
    const styleOpts = STYLES.map((s) => [s, s]);
    const colorOpts = Object.entries(COLORS).filter(([k]) => k !== "magenta");
    fillSelect(styleSel, styleOpts, P.style);
    fillSelect(colorSel, colorOpts, P.color);
    fillSelect($("addstyle"), styleOpts, "sticks");
    fillSelect($("addcolor"), Object.entries(COLORS), "element");

    let playing = false, surfacesStale = true, surfTimer = null;

    function applyStyle() {
      const style = styleSel.value, color = colorSel.value;
      viewer.setStyle({}, {});
      if ((style === "cartoon" || style === "surface") && !hasSS) {
        // no secondary structure at all (peptide, small molecule): fall back to sticks
        viewer.setStyle(baseSel, rep("sticks", color === "ss" ? "element" : color));
      } else {
        viewer.setStyle(baseSel, rep(style, color));
        if ((style === "cartoon" || style === "surface") && hetSerials.length) {
          viewer.setStyle({ serial: hetSerials }, { stick: { radius: 0.25, colorscheme: "default" } });
        }
      }
      for (const ly of layers) {
        if (ly.visible && ly.style !== "surface") viewer.addStyle(ly.sel, rep(ly.style, ly.color));
      }
      surfacesStale = true;
      redrawOverlays();
    }

    // surfaces and labels do not follow setFrame, so they are rebuilt for the current frame
    function redrawSurfaces() {
      viewer.removeAllSurfaces();
      surfacesStale = false;
      const opaque = (ly) => Object.assign({ opacity: 0.85 }, colorSpec(ly.color, resiRange));
      if (styleSel.value === "surface") {
        viewer.addSurface("SES", Object.assign({ opacity: 0.75 }, colorSpec(colorSel.value, resiRange)), baseSel);
      }
      for (const ly of layers) {
        if (ly.visible && ly.style === "surface") viewer.addSurface("SES", opaque(ly), ly.sel);
      }
    }
    function redrawLabels() {
      viewer.removeAllLabels();
      for (const s of labelled.values()) {
        const a = model.selectedAtoms({ serial: s })[0];
        if (!a) continue;
        viewer.addLabel(`${a.resn}${a.resi}${a.chain && a.chain.trim() ? ":" + a.chain : ""}`, {
          position: { x: a.x, y: a.y, z: a.z }, fontSize: 12, inFront: true,
          fontColor: dark ? "#f0f0f0" : "#111111",
          backgroundColor: dark ? "#333333" : "#ffffff", backgroundOpacity: 0.75,
        });
      }
    }
    function redrawOverlays() {
      // a surface takes a moment to build: during playback it is hidden, and after a frame
      // change it is rebuilt once the frame has stayed put for a moment (slider drags)
      clearTimeout(surfTimer);
      if (nFrames > 1) {
        viewer.removeAllSurfaces();
        if (!playing) surfTimer = setTimeout(() => { redrawSurfaces(); viewer.render(); }, 150);
      } else if (surfacesStale) redrawSurfaces();
      redrawLabels();
      viewer.render();
    }

    // --- layer panel ----------------------------------------------------------------
    const list = $("layers");
    function renderLayers() {
      if (!list) return;
      list.innerHTML = "";
      layers.forEach((ly, i) => {
        const row = document.createElement("span");
        row.className = "layer";
        const cb = document.createElement("input");
        cb.type = "checkbox"; cb.checked = ly.visible; cb.title = "show / hide";
        cb.onchange = () => { ly.visible = cb.checked; applyStyle(); };
        const name = document.createElement("span");
        name.className = "lname"; name.textContent = ly.name; name.title = ly.name;
        const st = document.createElement("select");
        fillSelect(st, styleOpts, ly.style);
        st.onchange = () => { ly.style = st.value; applyStyle(); };
        const co = document.createElement("select");
        fillSelect(co, Object.entries(COLORS), ly.color);
        co.onchange = () => { ly.color = co.value; applyStyle(); };
        const rm = document.createElement("button");
        rm.textContent = "✕"; rm.title = "remove layer";
        rm.onclick = () => { layers.splice(i, 1); renderLayers(); applyStyle(); };
        [cb, name, st, co, rm].forEach((x) => row.appendChild(x));
        list.appendChild(row);
      });
    }
    function addLayer() {
      const input = $("addsel");
      const text = (input.value || "").trim();
      if (!text) return;
      try {
        layers.push({ name: text, style: $("addstyle").value, color: $("addcolor").value, visible: true,
          sel: { serial: parseResidues(model, text) } });
        input.value = "";
        renderLayers();
        applyStyle();
      } catch (e) { flash(e.message); }
    }
    if ($("add")) $("add").onclick = addLayer;
    if ($("addsel")) {
      $("addsel").onkeydown = (e) => { if (e.key === "Enter") { e.preventDefault(); addLayer(); } };
    }
    if ($("clearlabels")) $("clearlabels").onclick = () => { labelled.clear(); redrawLabels(); viewer.render(); };

    function toggleLabel(atom) {
      const key = `${atom.chain}:${atom.resi}`;
      if (labelled.has(key)) labelled.delete(key); else labelled.set(key, atom.serial);
      redrawLabels();
      viewer.render();
    }

    styleSel.onchange = applyStyle;
    colorSel.onchange = applyStyle;
    $("reset").onclick = () => { viewer.zoomTo(); viewer.render(); };
    function setDark(d) {
      dark = d;
      setTheme(d);
      viewer.setBackgroundColor(d ? "#121212" : "#ffffff");
      redrawLabels();
      viewer.render();
    }
    if ($("theme")) $("theme").onclick = () => setDark(!dark);
    window.addEventListener("resize", () => viewer.resize());

    // --- trajectory controls -------------------------------------------------------
    let cur = 0, timer = null;
    const ctrl = $("ctrl");
    const play = $("play"), slider = $("frame");
    const fpsSel = $("fps"), label = $("flabel");

    function showFrame(i, cb) {
      cur = ((i % nFrames) + nFrames) % nFrames;
      slider.value = cur;
      const t = P.times_ps ? fmtTime(P.times_ps[cur]) : "";
      label.textContent = `frame ${P.frame_indices ? P.frame_indices[cur] : cur}` + (t ? ` · ${t}` : "");
      viewer.setFrame(cur).then(() => { redrawOverlays(); if (cb) cb(); });
    }
    function tick() {
      if (!playing) return;
      showFrame(cur + 1, () => { timer = setTimeout(tick, 1000 / Number(fpsSel.value)); });
    }
    function setPlaying(on) {
      const was = playing;
      playing = on;
      play.textContent = on ? "❚❚" : "▶";
      clearTimeout(timer);
      if (on) tick();
      else if (was) redrawOverlays();   // rebuild the surface hidden during playback
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
    }

    renderLayers();
    applyStyle();
    viewer.zoomTo();
    if (ctrl && nFrames > 1) showFrame(0);
    viewer.render();

    return {
      viewer,
      layers,
      labelled,
      resize: () => viewer.resize(),
      setDark,
      showFrame,
      setPlaying,
      addLayer,
      applyStyle,
    };
  }

  return { mount, setTheme, decodeCoords, parseResidues };
})();
