// Papermorph science book: the cast (load after engine.js). The notebook's owner (a kid in a yellow hoodie) and the
// dog, flat vector figures on a simple skeleton, so any pose can be set or blended at any moment of a beat.
// Both are drawn around the point between their feet and face +x; flip with face(-1).
'use strict';
const CAST = { skin: '#c98d63', skinDk: '#a8704c', hair: '#3a2a22', hoodie: '#f2c94c', hoodieDk: '#d9ab2c', jeans: '#3d5584',
  jeansDk: '#2e4268', shoe: '#f4f1e8', sole: '#9aa3b5', glasses: '#1d2333', fur: '#f3e6cf', furDk: '#d8c3a0', patch: '#a0673f',
  nose: '#2a2320', collar: '#e5533d' };

// Poses: segment angles in degrees from hanging straight down, positive swinging forward (+x).
// Arms [upper, fore], legs [thigh, shin]; head tilt (positive nods forward/down), look (eyes up, 0..1).
const KID_POSE = {
  stand: { ba: [-6, -4], fa: [8, 14], bl: [-3, 0], fl: [4, 0], head: 0, look: 0, lean: 0 },
  point: { ba: [-8, -6], fa: [128, 118], bl: [-3, 0], fl: [4, 0], head: -8, look: .4, lean: 0 },
  pointUp: { ba: [-8, -6], fa: [152, 160], bl: [-3, 0], fl: [4, 0], head: -18, look: 1, lean: -3 },
  lookUp: { ba: [-10, 20], fa: [14, 40], bl: [-3, 0], fl: [4, 0], head: -20, look: 1, lean: -3 },
  hold: { ba: [24, 80], fa: [40, 84], bl: [-3, 0], fl: [4, 0], head: 6, look: 0, lean: 0 },
  shrug: { ba: [-34, 70], fa: [34, 70], bl: [-3, 0], fl: [4, 0], head: -6, look: .2, lean: 0 },
  think: { ba: [-6, -4], fa: [40, 150], bl: [-3, 0], fl: [4, 0], head: -10, look: .7, lean: 0 },
};
const blendPose = (a, b, q) => Object.fromEntries(Object.keys(a).map(k => [k, Array.isArray(a[k]) ? a[k].map((v, i) => v + (b[k][i] - v) * q) : a[k] + (b[k] - a[k]) * q]));
// Walking: a pose from the stride phase (radians); one stride = 2*PI. Drive it from the distance walked.
function walkPose(ph) {
  const s = Math.sin(ph);
  return { ba: [24 * s, 24 * s + 18], fa: [-24 * s, -24 * s + 18], bl: [-26 * s, -26 * s - 30 * Math.max(0, s)],
    fl: [26 * s, 26 * s - 30 * Math.max(0, -s)], head: 2, look: 0, lean: 3 };
}

const limbAt = (x, y, len, [a1, a2]) => {
  const r = Math.PI / 180, x1 = x + len[0] * Math.sin(a1 * r), y1 = y + len[0] * Math.cos(a1 * r);
  return [x1, y1, x1 + len[1] * Math.sin(a2 * r), y1 + len[1] * Math.cos(a2 * r)];
};

function kid(p, { x = 0, y = 0, s = 1, o = 1, face = 1, pose = 'stand' } = {}) {
  const g = G(p, { x, y, s, o }), flip = mk('g', {}, g);
  const H = -118, SH = -192, ARM = [48, 46], LEG = [58, 56];
  const shadow = mk('ellipse', { cx: 0, cy: 2, rx: 46, ry: 8, fill: '#000', opacity: .22 }, flip);
  const body = mk('g', {}, flip);
  const limb = (c, w) => path(body, '', { stroke: c, 'stroke-width': w });
  const bLeg = limb(CAST.jeansDk, 24), bShoe = mk('ellipse', { rx: 19, ry: 10, fill: CAST.sole }, body);
  const bArm = limb(CAST.hoodieDk, 20), bHand = mk('circle', { r: 10, fill: CAST.skinDk }, body);
  const fLeg = limb(CAST.jeans, 24), fShoe = mk('ellipse', { rx: 20, ry: 10, fill: CAST.shoe }, body);
  const torso = mk('g', {}, body);
  path(torso, `M-36 ${SH + 4}Q0 ${SH - 14} 36 ${SH + 4}L33 ${H + 6}Q0 ${H + 14} -33 ${H + 6}Z`, { fill: CAST.hoodie, stroke: 'none' });
  path(torso, `M-14 ${SH - 2}Q0 ${SH + 16} 14 ${SH - 2}`, { stroke: CAST.hoodieDk, 'stroke-width': 4 });
  path(torso, `M-20 ${H - 26}H20`, { stroke: CAST.hoodieDk, 'stroke-width': 4 });
  path(torso, `M-6 ${SH + 8}v22M6 ${SH + 8}v18`, { stroke: CAST.shoe, 'stroke-width': 3 });
  const head = mk('g', {}, body);
  mk('circle', { cx: 0, cy: 0, r: 36, fill: CAST.skin }, head);
  path(head, 'M-38 -2C-44 -30 -24 -50 2 -46C26 -50 44 -30 36 -8C30 -22 18 -26 8 -24C-6 -30 -22 -24 -30 -10Z', { fill: CAST.hair, stroke: 'none' });
  mk('circle', { cx: -34, cy: 4, r: 8, fill: CAST.skinDk }, head);
  const eyes = mk('g', {}, head);
  const lens = (cx) => { mk('circle', { cx, cy: 2, r: 11, fill: '#ffffff', 'fill-opacity': .18, stroke: CAST.glasses, 'stroke-width': 3.5 }, head); };
  lens(4); lens(28); path(head, 'M15 2h2M-7 0L-30 -4', { stroke: CAST.glasses, 'stroke-width': 3.5 });
  const pupils = [mk('circle', { cx: 6, cy: 3, r: 3.6, fill: CAST.glasses }, eyes), mk('circle', { cx: 30, cy: 3, r: 3.6, fill: CAST.glasses }, eyes)];
  const mouth = path(head, 'M12 20Q18 25 25 20', { stroke: CAST.nose, 'stroke-width': 3 });
  const fArm = limb(CAST.hoodie, 20), fHand = mk('circle', { r: 10.5, fill: CAST.skin }, body);
  const prop = G(body);       // things held in the front hand go here, drawn around the hand
  let cur = KID_POSE.stand, hand = [0, 0], lastKey = '';
  const set = (P) => {
    const key = JSON.stringify(P); if (key === lastKey) return; lastKey = key; cur = P;
    body.setAttribute('transform', `rotate(${P.lean} 0 ${H})`);
    const leg = (el, shoe, hx, a) => { const [kx, ky, fx, fy] = limbAt(hx, H, LEG, a); el.setAttribute('d', `M${hx} ${H}L${kx} ${ky}L${fx} ${fy}`);
      shoe.setAttribute('cx', fx + 8); shoe.setAttribute('cy', fy + 4); };
    leg(bLeg, bShoe, -12, P.bl); leg(fLeg, fShoe, 12, P.fl);
    const arm = (el, hd, sx, a) => { const [ex, ey, hx, hy] = limbAt(sx, SH + 8, ARM, a); el.setAttribute('d', `M${sx} ${SH + 8}L${ex} ${ey}L${hx} ${hy}`);
      hd.setAttribute('cx', hx); hd.setAttribute('cy', hy); return [hx, hy]; };
    arm(bArm, bHand, -24, P.ba); hand = arm(fArm, fHand, 24, P.fa);
    head.setAttribute('transform', `translate(4 ${SH - 40}) rotate(${P.head})`);
    pupils.forEach(e => e.setAttribute('transform', `translate(${1 + P.look}, ${-3.5 * P.look})`));
    prop.setAttribute('transform', `translate(${hand[0]} ${hand[1]})`);
  };
  Object.assign(g, { prop, mouth,
    pose(a, b, q = 0) { const A = typeof a === 'string' ? KID_POSE[a] : a, B = typeof b === 'string' ? KID_POSE[b] : b; set(B ? blendPose(A, B, q) : A); return g; },
    walk(dist, step = 30) { set(walkPose(dist / step * Math.PI)); return g; },
    face(d) { flip.setAttribute('transform', d < 0 ? 'scale(-1 1)' : ''); g._face = d; return g; },
    // The front hand in the coordinates of the kid's parent (needs the group's state x, y, s).
    hand() { const S0 = st(g), d = g._face || 1, a = cur.lean * Math.PI / 180, hx = hand[0], hy = hand[1] - H;
      return [S0.x + d * S0.s * (hx * Math.cos(a) - hy * Math.sin(a)), S0.y + S0.s * (H + hx * Math.sin(a) + hy * Math.cos(a))]; },
    talk(open) { mouth.setAttribute('d', open ? 'M12 19Q18 30 25 19Z' : 'M12 20Q18 25 25 20'); return g; },
    blink(closed) { eyes.setAttribute('transform', closed ? 'translate(0 3) scale(1 .15)' : ''); return g; },
  });
  g.face(face);
  return g.pose(pose);
}

// The dog. Methods: d.wag(t) (tail from a time), d.walk(dist), d.sit(q) (0 standing .. 1 sitting), d.tilt(deg) (head).
function dog(p, { x = 0, y = 0, s = 1, o = 1, face = 1 } = {}) {
  const g = G(p, { x, y, s, o }), flip = mk('g', {}, g);
  mk('ellipse', { cx: 0, cy: 2, rx: 56, ry: 8, fill: '#000', opacity: .22 }, flip);
  const legs = [-30, -16, 22, 36].map((lx, i) => path(flip, '', { stroke: i % 2 ? CAST.fur : CAST.furDk, 'stroke-width': 13 }));
  const torso = mk('g', {}, flip);
  const tail = path(torso, 'M0 0C-14 -10 -22 -26 -18 -40', { stroke: CAST.fur, 'stroke-width': 10 });
  mk('ellipse', { cx: 0, cy: -50, rx: 48, ry: 27, fill: CAST.fur }, torso);
  path(torso, 'M-34 -66C-20 -78 4 -76 10 -64C2 -56 -24 -54 -34 -66Z', { fill: CAST.patch, stroke: 'none' });
  const head = mk('g', {}, torso);
  mk('circle', { cx: 0, cy: 0, r: 25, fill: CAST.fur }, head);
  mk('ellipse', { cx: 20, cy: 7, rx: 17, ry: 12, fill: CAST.fur }, head);
  mk('circle', { cx: 35, cy: 3, r: 5.5, fill: CAST.nose }, head);
  const eye = mk('ellipse', { cx: 9, cy: -6, rx: 3.8, ry: 4.2, fill: CAST.nose }, head);
  path(head, 'M18 15Q24 19 30 14', { stroke: CAST.nose, 'stroke-width': 2.5 });
  const ear = path(head, 'M-10 -20C-26 -22 -30 0 -22 14C-16 18 -10 6 -6 -14Z', { fill: CAST.patch, stroke: 'none' });
  path(torso, 'M34 -66Q44 -50 52 -60', { stroke: CAST.collar, 'stroke-width': 7 });
  let st0 = { walk: 0, sit: 0, wag: 0, tilt: 0 }, last = '';
  const apply = () => {
    const k = JSON.stringify(st0); if (k === last) return; last = k;
    const { walk, sit, wag, tilt } = st0, sw = Math.sin(walk);
    torso.setAttribute('transform', `rotate(${-24 * sit} -30 -36)`);
    legs.forEach((l, i) => {
      const lx = [-30, -16, 22, 36][i], back = i < 2, a = (i === 0 || i === 3 ? 1 : -1) * 24 * sw * (1 - sit);
      const top = back ? -36 + 4 * sit : -38 - 22 * sit, fx = back ? lx + 26 * sit : lx - 6 * sit, r = a * Math.PI / 180, L = -top;
      l.setAttribute('d', back && sit > .5 ? `M${lx + 4} ${top}Q${lx + 30} ${-10} ${lx + 34} 0` : `M${lx} ${top}L${fx + L * Math.sin(r)} ${top + L * Math.cos(r)}`);
    });
    tail.setAttribute('transform', `translate(-44 -54) rotate(${wag})`);
    head.setAttribute('transform', `translate(48 -84) rotate(${tilt + 24 * sit})`);
    ear.setAttribute('transform', `rotate(${4 * Math.sin(walk * 2)})`);
  };
  Object.assign(g, {
    wag(t, amp = 22) { st0.wag = amp * Math.sin(t * 14); apply(); return g; },
    walk(dist, step = 26) { st0.walk = dist / step * Math.PI; apply(); return g; },
    sit(q) { st0.sit = q; apply(); return g; },
    tilt(deg) { st0.tilt = deg; apply(); return g; },
    blink(closed) { eye.setAttribute('ry', closed ? .8 : 4.2); return g; },
    face(d) { flip.setAttribute('transform', d < 0 ? 'scale(-1 1)' : ''); g._face = d; return g; },
  });
  apply(); g.face(face);
  return g;
}
