// Papermorph science book: the notebook's pen (load after engine.js).
// Vocabulary in yellow highlighter, definitions in green, important terms in blue pen, handwritten notes and the
// dog's speech bubbles, and force arrows that start at the point where the force acts.
'use strict';
const HAND = '"Patrick Hand","Comic Sans MS",cursive';
const INK = { hl: '#f7e15a', def: '#9be38a', pink: '#f6a6c8', blue: '#7cc4ff', ink: '#1d2333', paper: '#fbf8ef',
  force: '#ff7a59', note: '#f4f1e8' };
// Width of a string in a font, measured once the web font has loaded (chapters boot after document.fonts.ready).
function handW(str, size, font = HAND, weight = 400) { ctx2d.font = `${weight} ${size}px ${font}`; return ctx2d.measureText(str).width; }

// A word in highlighter: the swash is one thick stroke, drawn on left to right, then the ink. hlIn(g, t0) reveals it.
function hl(p, str, { x = 0, y = 0, size = 40, anchor = 'middle', color = INK.hl, font = HAND, weight = 400, o = 1, r = 0 } = {}) {
  const w = handW(str, size, font, weight), x0 = anchor === 'middle' ? -w / 2 : anchor === 'end' ? -w : 0;
  const g = G(p, { x, y, o, r }), pad = size * .3;
  g._sw = path(g, `M${x0 - pad} ${-size * .32}Q${x0 + w / 2} ${-size * .38} ${x0 + w + pad} ${-size * .3}`,
    { stroke: color, 'stroke-width': size * 1.12, 'stroke-linecap': 'butt', 'stroke-opacity': .95 }, { d: 0 });
  g._t = T(g, str, { x: x0, size, fill: INK.ink, font, weight, o: 0 });
  g._w = w;
  return g;
}
function hlIn(g, t0, dur = .45) { show(g, t0, .01); draw(g._sw, t0, dur); show(g._t, t0 + dur * .5, .3); return g; }

// Handwritten text; '\n' starts a new line.
function pen(p, str, { x = 0, y = 0, size = 32, fill = INK.note, anchor = 'start', r = 0, o = 0, lh = 1.12 } = {}) {
  const g = G(p, { x, y, r, o });
  str.split('\n').forEach((s, i) => T(g, s, { y: i * size * lh, size, fill, font: HAND, anchor }));
  return g;
}

// A speech bubble whose tail points at (x + tx, y + ty); the box sits centred above (x, y). Pops in with pop().
function bubble(p, str, { x = 0, y = 0, tx = -30, ty = 60, size = 30, o = 0, s = .6 } = {}) {
  const lines = str.split('\n'), w = Math.max(...lines.map(l => handW(l, size))) + size * 1.1, h = lines.length * size * 1.1 + size * .7;
  const g = G(p, { x, y, o, s });
  const bx = -w / 2, by = -h, bt = Math.max(bx + 14, Math.min(bx + w - 40, tx - 13));
  path(g, `M${bx + 16} ${by}H${bx + w - 16}Q${bx + w} ${by} ${bx + w} ${by + 16}V${-16}Q${bx + w} 0 ${bx + w - 16} 0H${bt + 26}L${tx} ${ty}L${bt} 0H${bx + 16}Q${bx} 0 ${bx} ${-16}V${by + 16}Q${bx} ${by} ${bx + 16} ${by}Z`,
    { fill: INK.paper, stroke: INK.ink, 'stroke-width': 3 });
  lines.forEach((l, i) => T(g, l, { y: by + size * .35 + (i + 1) * size * 1.02, size, fill: INK.ink, font: HAND, anchor: 'middle' }));
  return g;
}

// A force arrow: f.set(x, y, len, deg) draws it from (x, y) along screen angle deg (0 right, 90 down); the label
// rides beside the arrow's middle. Length stands for magnitude.
function forceArrow(p, { color = INK.force, w = 8, label = '', size = 26, o = 1 } = {}) {
  const g = G(p, { o }), line = path(g, '', { stroke: color, 'stroke-width': w }), head = path(g, '', { fill: color, stroke: color, 'stroke-width': 2 });
  const lab = label ? pen(g, label, { size, fill: color, anchor: 'middle', o: 1 }) : null;
  // a dark halo keeps the label readable where the arrow crosses a picture
  if (lab) [...lab.children].forEach(t => { t.setAttribute('stroke', '#0b1226'); t.setAttribute('stroke-width', size * .22); t.setAttribute('paint-order', 'stroke'); t.setAttribute('stroke-linejoin', 'round'); });
  let last = '';
  g.set = (x, y, len, deg) => {
    const key = [x, y, len, deg].join();
    if (key === last) return g; last = key;
    const a = deg * Math.PI / 180, c = Math.cos(a), s = Math.sin(a), hl = Math.min(len * .45, w * 3.2);
    const x1 = x + c * len, y1 = y + s * len, xb = x1 - c * hl, yb = y1 - s * hl;
    line.setAttribute('d', `M${x} ${y}L${xb} ${yb}`);
    head.setAttribute('d', `M${x1} ${y1}L${xb - s * w * 1.5} ${yb + c * w * 1.5}L${xb + s * w * 1.5} ${yb - c * w * 1.5}Z`);
    if (lab) put(lab, { x: x + c * len / 2 - s * (size * .9), y: y + s * len / 2 + c * (size * .9) + size * .3 });
    return g;
  };
  return g;
}
