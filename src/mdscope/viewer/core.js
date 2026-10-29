// Shared viewer logic for the standalone page (template.html) and the MCP App (app.html).
// Expects $3Dmol to be loaded and a DOM with #title, #meta, #style, #color, #reset, #viewer, #notes.
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

  function mount(P, opts) {
    opts = opts || {};
    const dark = opts.dark !== undefined ? opts.dark
      : !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
    setTheme(dark);

    document.getElementById("title").textContent = P.title;
    document.getElementById("meta").textContent =
      `${P.n_residues} residues · ${P.n_atoms} atoms · selection "${P.selection}"` +
      (P.n_frames_total > 1 ? ` · frame ${P.frame}/${P.n_frames_total - 1}` : "");
    document.getElementById("notes").textContent = (P.notes || []).join(" · ");

    const el = document.getElementById("viewer");
    el.innerHTML = "";
    const viewer = $3Dmol.createViewer(el,
      { backgroundColor: dark ? "#121212" : "#ffffff", antialias: true });
    const model = viewer.addModel(P.pdb, "pdb");

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

    applyStyle();
    viewer.zoomTo();
    viewer.render();

    return {
      viewer,
      resize: () => viewer.resize(),
      setDark: (d) => { setTheme(d); viewer.setBackgroundColor(d ? "#121212" : "#ffffff"); viewer.render(); },
    };
  }

  return { mount, setTheme };
})();
