// Papermorph science book: space scenes (load after engine.js).
// Sun, Earth and Moon from NASA images (see img/CREDITS.md), lit by a night overlay that always faces away from the
// light; sunlight rays, shadow cones and orbits drawn in code.
'use strict';
const SKY = { deep: '#0b1226', mid: '#16214a', star: '#dfe6ff', sun: '#ffcf5a', light: '#ffe08a', night: '#050916',
  orbit: '#8d9bc4', axis: '#f4f1e8', umbra: '#03050b', penumbra: '#2b3150', rim: '#8cc8ff' };
const IMG = '../img/';
let spaceN = 0;
const uid = k => k + (++spaceN);
// Deterministic random numbers, so a replayed scene draws the same stars.
function rng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
  t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const dotsPath = pts => pts.map(([x, y, r]) => `M${x - r} ${y}a${r} ${r} 0 1 0 ${2 * r} 0a${r} ${r} 0 1 0 ${-2 * r} 0`).join('');

// Night sky over [x, y, w, h]: a gradient and two layers of stars, each one path.
function spaceBg(p, { x = 0, y = 0, w = 1600, h = 900, n = 160, seed = 7, o = 1 } = {}) {
  const g = G(p, { o }), id = uid('sky');
  const gr = mk('radialGradient', { id, cx: '50%', cy: '40%', r: '75%' }, mk('defs', {}, g));
  mk('stop', { offset: 0, 'stop-color': SKY.mid }, gr); mk('stop', { offset: 1, 'stop-color': SKY.deep }, gr);
  mk('rect', { x, y, width: w, height: h, fill: `url(#${id})` }, g);
  const R = rng(seed), big = [], small = [];
  for (let i = 0; i < n; i++) (R() < .18 ? big : small).push([x + R() * w, y + R() * h, R() < .18 ? 2.2 : 1.2]);
  path(g, dotsPath(small), { fill: SKY.star, "fill-opacity": .55, stroke: 'none' });
  path(g, dotsPath(big), { fill: SKY.star, "fill-opacity": .9, stroke: 'none' });
  return g;
}

// The sun: a soft glow and the SDO disc.
function sunBody(p, { x = 0, y = 0, r = 90, glow = 2.4, o = 1, s = 1 } = {}) {
  const g = G(p, { x, y, o, s }), id = uid('glow');
  const gr = mk('radialGradient', { id }, mk('defs', {}, g));
  [[0, .55], [.42, .28], [1, 0]].forEach(([k, a]) => mk('stop', { offset: k, 'stop-color': SKY.sun, 'stop-opacity': a }, gr));
  g._glow = mk('circle', { r: r * glow, fill: `url(#${id})` }, g);
  mk('image', { href: IMG + 'sun.webp', x: -r, y: -r, width: 2 * r, height: 2 * r }, g);
  return g;
}

// The dark part of a ball of radius r lit from +x (rotate the path toward the light). c is the cosine of the angle
// between the light and the viewer's line of sight: 1 fully lit (light behind the viewer), 0 half, -1 all dark.
function phasePath(r, c) {
  const k = Math.max(.001, Math.abs(c)) * r;
  return `M0 ${-r}A${r} ${r} 0 0 0 0 ${r}A${k} ${r} 0 0 ${c > 0 ? 1 : 0} 0 ${-r}Z`;
}

// A lit ball. kind: 'earth' (spinning side view from 120 frames), 'pole' (Earth from above the North Pole),
// 'earthBig', 'moon', 'moonFar', or a colour for a plain disc. Methods (call from clockRun/prog, pure in t):
//   b.spin(deg)        eastward turn: side view picks frames (cross-fading 3 degree steps); others rotate the
//                      image counterclockwise, which is eastward for the pole view
//   b.light(deg, c)    light arrives from screen angle deg (0 right, 90 down); c as in phasePath
//   b.tilt(deg)        lean the body and its axis (positive: north pole toward +x); the night side stays put
//   b.axis             the axis group (hidden); b.body the tilted group; b.night the overlay
const EARTH_SHEET = { w: 256, n: 120, cols: 12, step: 3 };
function globe(p, { x = 0, y = 0, r = 100, kind = 'earth', light = 180, c = 0, tilt = 0, spin = 0, night = .78, rim = true, o = 1, s = 1 } = {}) {
  const g = G(p, { x, y, o, s }), body = G(g, { r: tilt });
  let frames = null, img = null;
  if (kind === 'earth') {
    const W = EARTH_SHEET.w;
    frames = [0, 1].map(() => {
      const sv = mk('svg', { x: -r, y: -r, width: 2 * r, height: 2 * r, viewBox: `0 0 ${W} ${W}` }, body);
      mk('image', { href: IMG + 'earth_side.webp', width: W * EARTH_SHEET.cols, height: W * EARTH_SHEET.n / EARTH_SHEET.cols }, sv);
      return sv;
    });
  } else if (kind.startsWith('#')) {
    img = mk('circle', { r, fill: kind }, body);
  } else {
    const file = { pole: 'earth_pole', earthBig: 'earth_big', moon: 'moon_near', moonFar: 'moon_far' }[kind];
    img = mk('image', { href: IMG + file + '.webp', x: -r, y: -r, width: 2 * r, height: 2 * r }, body);
  }
  const dark = G(g, { r: light }), shade = path(dark, phasePath(r + .5, c), { fill: SKY.night, "fill-opacity": night, stroke: 'none' });
  const axisT = G(g, { r: tilt }), axis = G(axisT, { o: 0 });      // above the night side, leaning with the body
  path(axis, `M0 ${-r * 1.38}V${r * 1.38}`, { stroke: SKY.axis, 'stroke-width': Math.max(2.5, r * .035), 'stroke-dasharray': `${r * .09} ${r * .07}` });
  mk('circle', { cy: -r * 1.38, r: Math.max(4, r * .05), fill: SKY.axis }, axis);
  if (rim) mk('circle', { r: r + 1.5, fill: 'none', stroke: SKY.rim, 'stroke-width': Math.max(2, r * .03), opacity: kind === 'earth' || kind === 'pole' || kind === 'earthBig' ? .55 : .18 }, g);
  let lastF = -1, lastQ = -1, lastC = c;
  Object.assign(g, { body, axis, night: dark, r,
    spin(deg) {
      if (!frames) { put(img, { r: kind === 'pole' ? -deg : deg }); return g; }
      const f = (((deg / EARTH_SHEET.step) % EARTH_SHEET.n) + EARTH_SHEET.n) % EARTH_SHEET.n, i = Math.floor(f), q = +(f - i).toFixed(3);
      const vb = k => { const W = EARTH_SHEET.w; return `${(k % EARTH_SHEET.cols) * W} ${Math.floor(k / EARTH_SHEET.cols) * W} ${W} ${W}`; };
      if (i !== lastF) { frames[0].setAttribute('viewBox', vb(i)); frames[1].setAttribute('viewBox', vb((i + 1) % EARTH_SHEET.n)); lastF = i; }
      if (q !== lastQ) { frames[1].setAttribute('opacity', q); lastQ = q; }
      return g;
    },
    light(deg, cc = lastC) { put(dark, { r: deg }); if (cc !== lastC) { shade.setAttribute('d', phasePath(r + .5, cc)); lastC = cc; } return g; },
    tilt(deg) { put(body, { r: deg }); put(axisT, { r: deg }); return g; },
  });
  return g.spin(spin);
}

// Parallel sunlight: n lines from x0 to x1 across [y0, y1] (left to right, or reversed when x1 < x0), each with a
// small arrowhead. Returns the group; its paths carry {d: 0} so draw(g._lines[i], t0) runs them on.
function sunRays(p, { x0, x1, y0, y1, n = 5, w = 4, color = SKY.light, o = 1 } = {}) {
  const g = G(p, { o }), dir = Math.sign(x1 - x0);
  g._lines = Array.from({ length: n }, (_, i) => {
    const y = n === 1 ? y0 : y0 + (y1 - y0) * i / (n - 1);
    return path(g, `M${x0} ${y}H${x1}M${x1 - 18 * dir} ${y - 10}L${x1} ${y}L${x1 - 18 * dir} ${y + 10}`, { stroke: color, 'stroke-width': w }, { d: 0 });
  });
  return g;
}
const raysOn = (g, t0, dur = .8, gap = .08) => g._lines.forEach((l, i) => draw(l, t0 + i * gap, dur));

// The shadow behind a ball of radius r at (x, y) lit by a source of radius rs at distance dist along screen angle
// ang (pointing from the source to the ball). Umbra: the cone that sees none of the source; penumbra: part of it.
// Lengths come from similar triangles, so a smaller ball or a nearer source shortens the umbra.
function shadowCone(p, { x = 0, y = 0, r, rs, dist, ang = 0, len = 600, o = 1 } = {}) {
  const g = G(p, { x, y, r: ang, o });
  const ku = (rs - r) / dist, kp = (rs + r) / dist;              // narrowing of the umbra, widening of the penumbra
  const L = Math.min(len, r / Math.max(1e-6, ku)), hu = Math.max(0, r - ku * L);
  const pen = path(g, `M0 ${-r}L${len} ${-r - kp * len}V${r + kp * len}L0 ${r}Z`, { fill: SKY.penumbra, "fill-opacity": .55, stroke: 'none' });
  const um = path(g, `M0 ${-r}L${L} ${-hu}V${hu}L0 ${r}Z`, { fill: SKY.umbra, "fill-opacity": .85, stroke: 'none' });
  Object.assign(g, { umbra: um, penumbra: pen });
  return g;
}

// Orbits: an ellipse (optionally seen at a slant, ry < rx) and points on it, angle in degrees counterclockwise from +x.
const orbitAt = (cx, cy, rx, ry, deg) => [cx + rx * Math.cos(deg * Math.PI / 180), cy - ry * Math.sin(deg * Math.PI / 180)];
function orbit(p, cx, cy, rx, ry, { color = SKY.orbit, w = 3, dash = '10 12', o = 1 } = {}) {
  return path(p, `M${cx - rx} ${cy}A${rx} ${ry} 0 1 0 ${cx + rx} ${cy}A${rx} ${ry} 0 1 0 ${cx - rx} ${cy}`, { stroke: color, 'stroke-width': w, 'stroke-dasharray': dash, "stroke-opacity": o });
}
// A curved arrow along a circle of radius R around (cx, cy) from angle a0 to a1 (degrees, counterclockwise from +x).
function spinArrow(p, cx, cy, R, a0, a1, { color = SKY.axis, w = 5, ry = R } = {}) {
  const P = a => orbitAt(cx, cy, R, ry, a), [x0, y0] = P(a0), [x1, y1] = P(a1), sweep = a1 > a0 ? 0 : 1;
  const [xb, yb] = P(a1 - Math.sign(a1 - a0) * 9), ang = Math.atan2(y1 - yb, x1 - xb);
  const hd = (da) => [x1 - 18 * Math.cos(ang + da), y1 - 18 * Math.sin(ang + da)];
  const [h1, h2] = [hd(.5), hd(-.5)];
  return path(p, `M${x0} ${y0}A${R} ${ry} 0 ${Math.abs(a1 - a0) > 180 ? 1 : 0} ${sweep} ${x1} ${y1}M${h1[0]} ${h1[1]}L${x1} ${y1}L${h2[0]} ${h2[1]}`, { stroke: color, 'stroke-width': w }, { d: 0 });
}
