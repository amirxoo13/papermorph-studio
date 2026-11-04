// Chalk sketches for the unit headers on the contents page, one per unit, drawn in the unit's colour.
// Each is the inside of an SVG with viewBox 0 0 600 180. Classes:
//   d  a line that draws itself in when the unit scrolls into view (--k orders the strokes)
//   t  text or a filled shape that fades in
//   a  the faint chalk-white colour instead of the unit colour
// Loop classes (swap-a, hop, spin, tilt, ...) start after the drawing and are styled in index.html.
'use strict';
(() => {
  let k = 0;
  const P = (d, cls = '', extra = '') => `<path class="d ${cls}" pathLength="1" style="--k:${k++}" d="${d}" ${extra}/>`;
  const Tx = (x, y, s, size = 24, cls = '', anchor = 'start') => `<text class="t ${cls}" style="--k:${k++}" x="${x}" y="${y}" font-size="${size}" text-anchor="${anchor}">${s}</text>`;
  const C = (cx, cy, r, cls = '') => `<circle class="d ${cls}" pathLength="1" style="--k:${k++}" cx="${cx}" cy="${cy}" r="${r}"/>`;
  const dotC = (cx, cy, r, cls = '') => `<circle class="t ${cls}" style="--k:${k++}" cx="${cx}" cy="${cy}" r="${r}" fill="currentColor" stroke="none"/>`;
  const reset = s => { k = 0; return s; };
  const parab = (cx, cy, a, x0, x1) => {   // y = cy − a(x − cx)² in screen space (a > 0 opens up on screen)
    let d = '';
    for (let i = 0; i <= 40; i++) { const x = x0 + (x1 - x0) * i / 40; d += `${i ? 'L' : 'M'}${x.toFixed(1)} ${(cy - a * (x - cx) ** 2).toFixed(1)}`; }
    return d;
  };
  const sq = (x, y, s, cls = '') => P(`M${x} ${y}h${s}v${s}h${-s}Z`, cls);
  const grid = (x, y, n, u) => { let d = ''; for (let i = 1; i < n; i++) d += `M${x + i * u} ${y}v${n * u}M${x} ${y + i * u}h${n * u}`; return d; };

  window.UNIT_ART = [
    // 1 Arithmetic properties: grouping, a and b trading places, the order-of-operations ladder.
    reset(Tx(30, 70, '(2 + 3) + 4', 26, 'a') + Tx(30, 112, '2 + (3 + 4)', 26, 'a') + P('M30 80H170', 'a faint') +
      `<g class="swap-a">${Tx(258, 118, 'a', 44)}</g>${Tx(290, 116, '+', 36, 'a')}<g class="swap-b">${Tx(338, 118, 'b', 44)}</g>` +
      P('M268 74Q305 30 344 74') + P('M344 128Q305 168 268 128') + P('M336 66l8 8 4-11') + P('M276 136l-8-8-4 11') +
      [['( )', 0], ['x²', 1], ['× ÷', 2], ['+ −', 3]].map(([s, i]) => P(`M${450 + i * 34} ${56 + i * 34}h${150 - i * 34}`, 'a') + Tx(460 + i * 34, 50 + i * 34, s, 20, 'step')).join('')),
    // 2 The number system: a number line with hops from −3 to 2.
    reset(P('M28 130H572') + P('M560 122l12 8-12 8') + P('M40 122l-12 8 12 8') +
      Array.from({ length: 11 }, (_, i) => P(`M${50 + i * 50} 122v16`, 'a') + Tx(50 + i * 50, 162, i - 5 < 0 ? '−' + (5 - i) : String(i - 5), 17, 'a', 'middle')).join('') +
      P('M150 116Q175 84 200 116Q225 84 250 116Q275 84 300 116Q325 84 350 116Q375 84 400 116', 'a faint') +
      `<circle class="t hop" cx="0" cy="0" r="8" fill="currentColor" stroke="none" style="--k:${k++};offset-path:path('M150 116Q175 84 200 116Q225 84 250 116Q275 84 300 116Q325 84 350 116Q375 84 400 116')"/>` +
      Tx(40, 58, '¾ = 0.75', 26, 'a') + Tx(430, 58, '−3 + 5 = 2', 26)),
    // 3 Ratios, proportions, and percents: a filling pie, ratio bars, a percent tag.
    reset(C(110, 95, 62, 'a') + `<circle class="t pie" cx="110" cy="95" r="31" fill="none" stroke-width="62" pathLength="100" transform="rotate(-90 110 95)" style="--k:${k++}"/>` +
      Tx(110, 172, '25%', 20, 'a', 'middle') +
      [0, 1].map(i => sq(220 + i * 36, 52, 30)).join('') + [0, 1, 2].map(i => sq(220 + i * 36, 100, 30, 'a')).join('') + Tx(345, 92, '2 : 3', 26) +
      P('M440 58H560L590 95L560 132H440Z') + C(568, 95, 5) + Tx(500, 105, '40%', 28, '', 'middle') + Tx(500, 160, 'off', 18, 'a', 'middle')),
    // 4 Exponents and expressions: squares of 1, 2, 3, then x² and powers of ten.
    reset([[1, 30], [2, 70], [3, 140]].map(([n, x]) => sq(x, 160 - n * 30, n * 30) + (n > 1 ? P(grid(x, 160 - n * 30, n, 30), 'a faint') : '') + Tx(x + n * 15, 172 - n * 30 - 18, n + '²', 18, 'a', 'middle')).join('') +
      Tx(300, 92, 'x² + 3x', 36) + Tx(300, 140, '2³ = 8', 24, 'a') + Tx(460, 70, '10⁶', 36) + Tx(450, 140, '3.2 × 10⁵', 22, 'a')),
    // 5 Linear equations and inequalities: a balance with x + 3 = 7, and a ray.
    reset(Tx(24, 64, 'x + 3 = 7', 28) + Tx(24, 112, 'x = 4', 28, 'a') +
      P('M300 160L278 172H322Z', 'a') + P('M300 160V72', 'a') +
      `<g class="tilt">${P('M196 72H404')}${P('M210 72l-24 52M210 72l24 52M390 72l-24 52M390 72l24 52', 'a faint')}${P('M180 124Q210 140 240 124Z')}${P('M360 124Q390 140 420 124Z')}` +
      `${P('M190 98h22v22h-22Z')}${Tx(201, 115, 'x', 16, '', 'middle')}${[0, 1, 2].map(i => dotC(222 + i * 9, 116, 4)).join('')}${[0, 1, 2, 3, 4, 5, 6].map(i => dotC(368 + (i % 4) * 11, 116 - Math.floor(i / 4) * 10, 4)).join('')}</g>` +
      P('M470 140H590') + P('M580 132l10 8-10 8') + C(490, 140, 7) + Tx(476, 112, 'x > 2', 22, 'a')),
    // 6 Graphing linear equations: a grid with a line, a slope step, and a point riding the line.
    reset(P(grid(330, 20, 6, 25), 'a faint') + P('M330 95H490M405 20V170', 'a') +
      `<path class="t shade" style="--k:${k++}" d="M330 170L330 132L480 20L480 170Z" fill="currentColor" stroke="none"/>` +
      P('M330 132L480 20') + P('M380 95v-37h50', 'a') + Tx(372, 82, '3', 16, 'a', 'end') + Tx(405, 52, '4', 16, 'a', 'middle') +
      `<circle class="t ride" r="7" fill="currentColor" stroke="none" style="--k:${k++};offset-path:path('M330 132L480 20')"/>` +
      Tx(40, 70, 'y = mx + b', 32) + Tx(40, 120, 'm = rise ÷ run', 22, 'a') + Tx(520, 60, '(x, y)', 22, 'a')),
    // 7 Statistics and probability: a histogram, a spinner, a number cube.
    reset(P('M30 160H210', 'a') + [40, 80, 120, 70, 30].map((h, i) => P(`M${40 + i * 34} 160v${-h}h30v${h}`)).join('') +
      C(320, 95, 62) + P('M320 95V33M320 95L374 126M320 95L266 126', 'a') +
      `<g class="spin">${P('M320 95L320 48', '', 'stroke-width="4"')}${P('M313 58L320 44L327 58')}</g>` + dotC(320, 95, 6) +
      P('M460 52h80a12 12 0 0 1 12 12v80a12 12 0 0 1-12 12h-80a12 12 0 0 1-12-12v-80a12 12 0 0 1 12-12Z') +
      [[478, 70], [522, 70], [500, 104], [478, 138], [522, 138]].map(([x, y]) => dotC(x, y, 6)).join('')),
    // 8 Functions: x goes into the machine, f(x) comes out; a mapping diagram.
    reset(Tx(26, 64, 'f(x) = 2x + 1', 26) + P('M80 112H210', 'a') + P('M200 104l10 8-10 8', 'a') +
      P('M212 72h96v80h-96Z') + Tx(260, 126, 'f', 40, '', 'middle') + P('M310 112H400', 'a') + P('M390 104l10 8-10 8', 'a') +
      `<g class="feed-in">${Tx(110, 106, '3', 26, '', 'middle')}</g><g class="feed-out">${Tx(350, 106, '7', 26, '', 'middle')}</g>` +
      `<ellipse class="d a" pathLength="1" style="--k:${k++}" cx="460" cy="96" rx="22" ry="62"/><ellipse class="d a" pathLength="1" style="--k:${k++}" cx="560" cy="96" rx="22" ry="62"/>` +
      [[60, 70], [96, 70], [132, 120]].map(([a, b]) => P(`M470 ${a}L548 ${b}`)).join('') + [60, 96, 132].map(y => dotC(460, y, 4)).join('') + [70, 120].map(y => dotC(560, y, 4)).join('')),
    // 9 Polynomial operations: the area grid for (x + 2)(x + 3).
    reset(Tx(24, 72, '(x + 2)(x + 3)', 26) + Tx(24, 120, '= x² + 5x + 6', 26, 'a') +
      P('M300 30h140v140h-140Z') + P('M390 30v140M300 120h140', 'a') +
      [['x²', 345, 82, 0], ['2x', 415, 82, 1], ['3x', 345, 152, 2], ['6', 415, 152, 3]].map(([s, x, y, i]) => `<g class="cell" style="--j:${i}">${Tx(x, y, s, 22, '', 'middle')}</g>`).join('') +
      Tx(345, 22, 'x', 18, 'a', 'middle') + Tx(415, 22, '+2', 18, 'a', 'middle') + Tx(292, 82, 'x', 18, 'a', 'end') + Tx(292, 152, '+3', 18, 'a', 'end') +
      Tx(480, 82, '×', 26, 'a') + Tx(510, 82, 'FOIL', 22, 'a')),
    // 10 Factoring: a factor tree and the square with a corner cut away.
    reset(Tx(110, 40, '60', 26, '', 'middle') + P('M100 48L70 78M120 48L150 78') + Tx(64, 100, '6', 22, '', 'middle') + Tx(156, 100, '10', 22, '', 'middle') +
      P('M58 108L42 136M70 108L86 136M150 108L134 136M162 108L178 136', 'a') + ['2', '3', '2', '5'].map((s, i) => Tx([38, 90, 130, 182][i], 160, s, 20, 'a', 'middle')).join('') +
      P('M280 40h110v110h-110Z') + `<path class="t cut" style="--k:${k++}" d="M350 110h40v40h-40Z" fill="currentColor" stroke="none"/>` + P('M350 110v40M350 110h40', 'a faint') +
      Tx(430, 82, 'x² − 9', 28) + Tx(430, 128, '= (x + 3)(x − 3)', 22, 'a')),
    // 11 Radicals: a unit square's diagonal, a big radical, a little cube.
    reset(P('M40 50h90v90h-90Z', 'a') + P('M40 140L130 50', 'diag') + Tx(98, 110, '√2', 22, '', 'start') + Tx(40, 166, '1', 18, 'a') +
      P('M200 98l12-6 18 46 26-100h170') + Tx(266, 120, '72 = 6√2', 34) +
      P('M500 80l40-22 40 22v52l-40 22-40-22Z') + P('M500 80l40 22 40-22M540 102v52', 'a') + Tx(540, 176, '∛27 = 3', 18, 'a', 'middle')),
    // 12 Quadratic equations: a parabola crossing the x-axis at its two roots, and the formula.
    reset(P('M290 120H590M440 20V172', 'a') + P(parab(440, 160, .012, 330, 550)) +
      `<circle class="t root" cx="${440 - Math.sqrt(40 / .012)}" cy="120" r="7" fill="currentColor" stroke="none" style="--k:${k++}"/>` +
      `<circle class="t root" cx="${440 + Math.sqrt(40 / .012)}" cy="120" r="7" fill="currentColor" stroke="none" style="--k:${k++}"/>` +
      Tx(24, 58, 'ax² + bx + c = 0', 24) + Tx(24, 112, 'x =', 24, 'a') + Tx(150, 100, '−b ± √(b² − 4ac)', 20, 'a', 'middle') + P('M78 108H222', 'a') + Tx(150, 132, '2a', 20, 'a', 'middle')),
    // 13 Quadratic functions: a family of parabolas around a vertex and its axis of symmetry.
    reset(P('M260 150H500', 'a') + P('M380 20V172', 'a faint') +
      `<g class="breathe">${P(parab(380, 140, .02, 305, 455))}</g>` + P(parab(380, 140, .007, 265, 495), 'a') + P(parab(380, 40, -.005, 270, 490), 'a faint') +
      dotC(380, 140, 7) + Tx(396, 168, 'vertex', 16, 'a') + Tx(24, 70, 'y = a(x − h)² + k', 24) + Tx(24, 116, 'vertex (h, k)', 20, 'a') + Tx(510, 60, 'x = h', 20, 'a')),
  ];
})();
