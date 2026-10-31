// Build the viewer's VolumeData from a payload with the real 3Dmol.js, run its marching cubes at
// the payload's level and print the bounding box of the isosurface (in the viewer's coordinates).
// usage: node density_check.js <3Dmol-min.js> <core.js> <payload.json>
const fs = require("fs");
const [, , lib, coreJs, payloadJson] = process.argv;
global.window = global; global.self = global; global.navigator = { userAgent: "node" };
global.document = { createElement: () => ({ getContext: () => null, style: {} }), addEventListener() {},
  querySelectorAll: () => [] };
new Function(fs.readFileSync(lib, "utf8"))();
new Function(fs.readFileSync(coreJs, "utf8"))();
const P = JSON.parse(fs.readFileSync(payloadJson, "utf8"));
const vol = window.MdscopeViewer.volumeOf(P.density);
const shape = new $3Dmol.GLShape({});
shape.addIsosurface(vol, { isoval: P.density.level });
const v = shape.geo.geometryGroups[0].vertexArray;
const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
for (let i = 0; i < v.length; i++) { lo[i % 3] = Math.min(lo[i % 3], v[i]); hi[i % 3] = Math.max(hi[i % 3], v[i]); }
console.log(JSON.stringify({ n: v.length / 3, lo, hi }));
