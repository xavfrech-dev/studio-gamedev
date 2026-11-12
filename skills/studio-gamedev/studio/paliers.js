/* studio/paliers.js : le studio embellit avec le jeu.
   Cinq paliers (garage, petit bureau, studio, studio pro, studio AAA) liés au niveau du studio et à l'avancement
   de la roadmap. Chaque palier change le sol, les murs, l'éclairage, le mobilier et les effets ; le passage d'un
   palier se fait en chantier animé (poussière, échafaudage, perceuse). La palette du bureau est déduite des
   réponses du questionnaire (palette, ambiance, genre, cadre du monde) : jamais d'asset du jeu.
   Tout est tracé par code (aucune image, aucune police, aucun logo). */
(function () {
  'use strict';
  const NOMS = { fr: ['Garage', 'Petit bureau', 'Studio', 'Studio pro', 'Studio AAA'], en: ['Garage', 'Small office', 'Studio', 'Pro studio', 'AAA studio'] };
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const hex = v => typeof v === 'string' && /^#[0-9a-f]{6}$/i.test(v);
  function mix(a, b, k) { const pa = parseInt(a.slice(1), 16), pb = parseInt(b.slice(1), 16); const c = i => Math.round(((pa >> i) & 255) + ((((pb >> i) & 255) - ((pa >> i) & 255)) * k)); return '#' + ((c(16) << 16) | (c(8) << 8) | c(0)).toString(16).padStart(6, '0'); }
  function rgba(h, a) { const p = parseInt(h.slice(1), 16); return `rgba(${(p >> 16) & 255},${(p >> 8) & 255},${p & 255},${a})`; }
  const alea = (i, j = 0) => { let h = Math.imul(i * 374761393 + j * 668265263, 1274126177) >>> 0; h = Math.imul(h ^ (h >>> 13), 1103515245) >>> 0; return (h & 0xffff) / 0xffff; };

  // ---------------------------------------------------------------- palier depuis le niveau et la roadmap
  // niveau (rangs du gabarit : 1, 5, 10, 16, 24) ou avancement de la roadmap (15, 35, 60, 90 %) : le plus haut des deux
  function calculer(o) {
    o = o || {};
    if (o.force >= 1 && o.force <= 5) return Math.round(o.force);
    if (o.mode === 'accueil') return 1;
    const n = +o.niveau || 1, pct = +o.pct || 0;
    const parNiveau = n >= 24 ? 5 : n >= 16 ? 4 : n >= 10 ? 3 : n >= 5 ? 2 : 1;
    const parRoadmap = o.finie || pct >= 90 ? 5 : pct >= 60 ? 4 : pct >= 35 ? 3 : pct >= 15 ? 2 : 1;
    return Math.max(parNiveau, parRoadmap);
  }

  // ---------------------------------------------------------------- DA du bureau déduite des réponses
  const PALETTES = {
    chaude: { accent: '#d9893b', accent2: '#c4543a', mur: '#e8d6b6', sol: '#9a7652', bois: '#a8743f', lumiere: '#ffcf8a' },
    froide: { accent: '#4f8cc9', accent2: '#4fb0a4', mur: '#d6dee4', sol: '#7d8790', bois: '#8f7c68', lumiere: '#e3efff' },
    contrastee: { accent: '#e2483a', accent2: '#f2c230', mur: '#ecebe6', sol: '#55504c', bois: '#6b4a33', lumiere: '#fff1d6' },
    sourde: { accent: '#8f9c7a', accent2: '#b08a6e', mur: '#d9d3c5', sol: '#8a8174', bois: '#94806a', lumiere: '#f3e3c4' },
    vive: { accent: '#ef5d8f', accent2: '#2fbfa6', mur: '#f3ede1', sol: '#8d7b6b', bois: '#b78350', lumiere: '#ffe3a8' },
    defaut: { accent: '#b98532', accent2: '#4d6f9c', mur: '#d9c9a6', sol: '#8a6a48', bois: '#a0744a', lumiere: '#ffd59a' }
  };
  function theme(R, confTh) {
    R = R || {}; const v = id => R[id] && R[id].valeur;
    const pal = v('da.palette'), genre = v('genre.principal'), climat = v('monde.climat'), style = v('da.style');
    const emo = [].concat(v('vision.emotion') || []);
    const th = Object.assign({}, PALETTES[pal] || PALETTES.defaut);
    th.ombre = .2; th.vue = climat || 'campagne'; th.style = style || ''; th.palette = pal || '';
    if (genre === 'horreur') { th.ombre += .1; th.lumiere = mix(th.lumiere, '#c9d6ff', .35); th.mur = mix(th.mur, '#3a3a44', .25); th.accent2 = mix(th.accent2, '#7a2a2a', .4); }
    if (genre === 'visual_novel' || genre === 'puzzle' || emo.includes('detente')) th.ombre -= .04;
    if (emo.includes('tension')) th.ombre += .04;
    if (climat === 'desert') { th.mur = mix(th.mur, '#e7c99a', .3); th.plante = 'cactus'; }
    else if (climat === 'tropical') th.plante = 'palmier';
    else if (climat === 'espace') { th.plante = 'cristal'; th.accent2 = mix(th.accent2, '#6a5acd', .3); }
    else if (climat === 'souterrain') { th.plante = 'champignon'; th.ombre += .03; }
    else if (climat === 'mer') th.accent2 = mix(th.accent2, '#2f7fb0', .35);
    th.plante = th.plante || 'ficus';
    th.sol2 = mix(th.sol, '#000000', .09);
    const c = confTh || {}; for (const k of ['accent', 'accent2', 'sol', 'sol2', 'mur', 'bois', 'lumiere']) if (hex(c[k])) th[k] = c[k];
    th.ombre = clamp(th.ombre, .08, .4);
    th.cle = [th.accent, th.accent2, th.mur, th.sol, th.bois, th.lumiere, th.vue, th.plante].join('');
    return th;
  }

  // ---------------------------------------------------------------- rendu (G : accès au bureau de la page)
  function creer(G) {
    const W = G.W, H = G.H, HM = 5.8;     // taille de la pièce (cases) et hauteur des murs (demi-cases)
    const iso = G.iso, now = () => performance.now() / 1000;
    let cache = null, cacheCle = '', etat = { actuel: 0, ancien: 0, t0: 0 }, apparus = {};
    const DUREE = 7.5;                      // durée du chantier (s)
    const POUSS = [], ETINC = [], BRINS = [];
    let ombreCv = null;

    // -------- primitives (ctx explicite : sert aussi au cache)
    function poly(c, pts, fill, stroke, lw) { c.beginPath(); pts.forEach((p, i) => i ? c.lineTo(p[0], p[1]) : c.moveTo(p[0], p[1])); c.closePath(); if (fill) { c.fillStyle = fill; c.fill(); } if (stroke) { c.strokeStyle = stroke; c.lineWidth = lw || 1; c.stroke(); } }
    function boite(c, gx, gy, w, d, h, coul, z0 = 0, o = {}) {
      if (!z0 && o.ombre !== false) poly(c, [iso(gx + .06, gy + d), iso(gx + w + .14, gy + d), iso(gx + w + .14, gy + .1), iso(gx + w, gy), iso(gx + w, gy + d + .14), iso(gx + .1, gy + d + .14)], 'rgba(20,14,8,.16)');
      const s = o.trait === undefined ? 'rgba(0,0,0,.22)' : o.trait;
      poly(c, [iso(gx, gy + d, z0), iso(gx + w, gy + d, z0), iso(gx + w, gy + d, z0 + h), iso(gx, gy + d, z0 + h)], mix(coul, '#000000', .26), s);
      poly(c, [iso(gx + w, gy, z0), iso(gx + w, gy + d, z0), iso(gx + w, gy + d, z0 + h), iso(gx + w, gy, z0 + h)], mix(coul, '#000000', .12), s);
      const a = iso(gx, gy, z0 + h), b = iso(gx + w, gy + d, z0 + h), g = c.createLinearGradient(a[0], a[1], b[0], b[1]);
      g.addColorStop(0, mix(coul, '#ffffff', .1)); g.addColorStop(1, coul);
      poly(c, [a, iso(gx + w, gy, z0 + h), b, iso(gx, gy + d, z0 + h)], g, s);
    }
    // plan vertical : 'g' = plan x = fixe (comme le mur de gauche), 'd' = plan y = fixe (comme le mur de droite).
    // Repère local : x le long du plan (cases, depuis a), y vers le bas depuis z1 (demi-cases).
    function plan(c, type, fixe, a, z1, f) {
      const TW = G.TW(), TH = TW / 2, o = type === 'g' ? iso(fixe, a, z1) : iso(a, fixe, z1);
      c.save(); c.transform(type === 'g' ? -TW / 2 : TW / 2, TH / 2, 0, TH, o[0], o[1]); f(c, 1 / TH); c.restore();
    }
    function solPlan(c, z, f) { const TW = G.TW(), o = iso(0, 0, z); c.save(); c.transform(TW / 2, TW / 4, -TW / 2, TW / 4, o[0], o[1]); f(c, 2 / TW); c.restore(); }
    function ellipseSol(c, gx, gy, rx, ry, fill) { solPlan(c, 0, cc => { cc.fillStyle = fill; cc.beginPath(); cc.ellipse(gx, gy, rx, ry, 0, 0, 7); cc.fill(); }); }

    // -------- sol
    function sol(c, th, p) {
      solPlan(c, 0, (c, px) => {
        if (p === 1) {               // béton lissé : dalles, joints, taches, ligne peinte délavée
          const b = mix('#9a948a', th.sol, .22);
          for (let x = 0; x < W; x += 2) for (let y = 0; y < H; y += 2) { c.fillStyle = mix(b, alea(x, y) > .5 ? '#ffffff' : '#000000', alea(y, x) * .06); c.fillRect(x, y, 2, 2); }
          c.strokeStyle = 'rgba(40,34,28,.28)'; c.lineWidth = px * 1.2; for (let x = 0; x <= W; x += 2) { c.beginPath(); c.moveTo(x, 0); c.lineTo(x, H); c.stroke(); } for (let y = 0; y <= H; y += 2) { c.beginPath(); c.moveTo(0, y); c.lineTo(W, y); c.stroke(); }
          for (let i = 0; i < 9; i++) { c.fillStyle = `rgba(40,30,20,${.04 + alea(i, 9) * .05})`; c.beginPath(); c.ellipse(1 + alea(i, 1) * (W - 2), 1 + alea(i, 2) * (H - 2), .3 + alea(i, 3) * .7, .2 + alea(i, 4) * .4, alea(i, 5) * 3, 0, 7); c.fill(); }
          c.fillStyle = 'rgba(226,184,72,.22)'; c.fillRect(12.2, 7.6, .12, 3.6); c.fillRect(12.2, 11.1, 3.6, .12);
        } else if (p === 2) {        // stratifié clair, lames décalées
          const b = mix('#cfae84', th.bois, .3);
          for (let y = 0, r = 0; y < H; y += .42, r++) { let x = -alea(r, 1) * 2; while (x < W) { const l = 1.6 + alea(r, Math.round(x * 10)) * 1.6; c.fillStyle = mix(b, '#6b4a2b', alea(r, Math.round(x * 7)) * .14); c.fillRect(Math.max(0, x), y, Math.min(l, W - x), .42); c.fillStyle = 'rgba(60,40,20,.22)'; c.fillRect(x + l - px, y, px * 1.2, .42); x += l; } c.fillStyle = 'rgba(60,40,20,.18)'; c.fillRect(0, y, W, px); }
        } else if (p === 3) {        // dalles de moquette alternées
          const b = mix('#74777c', th.sol, .3);
          for (let x = 0; x < W; x++) for (let y = 0; y < H; y++) {
            c.fillStyle = mix(b, (x + y) % 2 ? '#ffffff' : '#000000', .035 + alea(x, y) * .02); c.fillRect(x, y, 1, 1);
            c.strokeStyle = 'rgba(255,255,255,.035)'; c.lineWidth = px; for (let k = .2; k < 1; k += .2) { c.beginPath(); if ((x + y) % 2) { c.moveTo(x + k, y); c.lineTo(x + k, y + 1); } else { c.moveTo(x, y + k); c.lineTo(x + 1, y + k); } c.stroke(); }
          }
          c.strokeStyle = 'rgba(0,0,0,.12)'; c.lineWidth = px; for (let x = 0; x <= W; x++) { c.beginPath(); c.moveTo(x, 0); c.lineTo(x, H); c.stroke(); } for (let y = 0; y <= H; y++) { c.beginPath(); c.moveTo(0, y); c.lineTo(W, y); c.stroke(); }
        } else {                     // parquet chaud (4) ou bois sombre ciré (5)
          const b = p === 4 ? mix('#b0743f', th.bois, .35) : mix('#6e4a30', th.bois, .2), e = p === 4 ? .3 : .34;
          for (let x = 0, r = 0; x < W; x += e, r++) { let y = -alea(r, 3) * 2.5; while (y < H) { const l = 2 + alea(r, Math.round(y * 9)) * 2; c.fillStyle = mix(b, alea(r, Math.round(y * 5)) > .5 ? '#ffffff' : '#2a1608', alea(Math.round(y * 3), r) * .1); c.fillRect(x, Math.max(0, y), e, Math.min(l, H - y)); c.strokeStyle = 'rgba(40,22,10,.12)'; c.lineWidth = px * .8; c.beginPath(); c.moveTo(x + e * .35, y + .2); c.lineTo(x + e * .4, y + l - .2); c.stroke(); c.fillStyle = 'rgba(30,16,6,.3)'; c.fillRect(x, y + l - px, e, px * 1.3); y += l; } c.fillStyle = 'rgba(30,16,6,.25)'; c.fillRect(x, 0, px, H); }
          if (p === 5) { const g = c.createLinearGradient(0, 0, W, H); g.addColorStop(0, 'rgba(255,240,220,.0)'); g.addColorStop(.45, 'rgba(255,240,220,.07)'); g.addColorStop(.55, 'rgba(255,240,220,.0)'); c.fillStyle = g; c.fillRect(0, 0, W, H); }
        }
        // tapis
        const tapis = (x, y, w, h, coul, bord, motif) => { c.fillStyle = 'rgba(0,0,0,.15)'; c.fillRect(x + .06, y + .06, w, h); c.fillStyle = coul; c.fillRect(x, y, w, h); c.strokeStyle = bord; c.lineWidth = .08; c.strokeRect(x + .14, y + .14, w - .28, h - .28); if (motif) { c.fillStyle = bord; for (let i = .6; i < w - .4; i += .7) c.fillRect(x + i, y + h / 2 - .05, .3, .1); } };
        if (p === 1) tapis(4.2, 7.55, 5.4, 1.1, mix('#8a5a44', th.accent2, .2), 'rgba(240,220,190,.35)', false);
        if (p >= 2) tapis(1.6, 7.5, 10.4, 1.25, mix(th.accent2, '#3a3028', .45), rgba(mix(th.accent, '#ffffff', .3), .55), p >= 3);
        if (p >= 3) tapis(3.5, 10.35, 2.8, 1.55, mix(th.accent, '#3a3028', .5), 'rgba(255,240,210,.35)', true);
        if (p >= 4) tapis(12.75, 9.75, 3.0, 1.9, mix('#3a4048', th.accent2, .2), 'rgba(255,255,255,.18)', false);
        if (p === 5) tapis(13.3, 4.3, 2.3, 1.7, mix(th.accent, '#1c1612', .55), rgba(th.accent, .7), true);
      });
    }

    // -------- murs (cache) : matière par palier, plinthe, arête
    function murs(c, th, p) {
      const faces = [['d', W, .06], ['g', H, .2]];
      for (const [type, L, sombre] of faces) {
        plan(c, type, 0, 0, HM, (c, px) => {
          let base;
          if (p === 1) base = mix('#bdb6aa', th.mur, .3);
          else if (p === 2) base = th.mur;
          else if (p === 3) base = type === 'g' ? mix(th.accent, th.mur, .5) : th.mur;
          else if (p === 4) base = mix(th.mur, '#fff6e6', .15);
          else base = mix(th.mur, '#2a2230', .26);   // AAA : sombre chic mais lisible
          c.fillStyle = mix(base, '#000000', sombre); c.fillRect(0, 0, L, HM);
          const g = c.createLinearGradient(0, 0, 0, HM); g.addColorStop(0, 'rgba(0,0,0,.10)'); g.addColorStop(.6, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,.06)'); c.fillStyle = g; c.fillRect(0, 0, L, HM);
          if (p === 1) {               // parpaings
            for (let y = 0, r = 0; y < HM; y += .62, r++) for (let x = (r % 2) * -.5; x < L; x += 1) { c.fillStyle = mix(mix(base, '#000000', sombre), alea(r, Math.round(x * 4)) > .5 ? '#ffffff' : '#000000', alea(Math.round(x * 3), r) * .07); c.fillRect(Math.max(0, x) + .03, y + .04, Math.min(1, L - x) - .06, .56); }
            c.strokeStyle = 'rgba(80,70,60,.25)'; c.lineWidth = px; c.beginPath(); c.moveTo(0, .55); c.lineTo(L, .55); c.stroke();
            c.fillStyle = '#6f6a62'; c.fillRect(0, .3, L, .14);                                    // gaine électrique
          } else if (p === 4) {        // lambris bois en bas
            c.fillStyle = mix(th.bois, '#000000', .1 + sombre * .5); c.fillRect(0, HM - 2, L, 2);
            c.strokeStyle = 'rgba(30,18,8,.3)'; c.lineWidth = px; for (let x = .25; x < L; x += .25) { c.beginPath(); c.moveTo(x, HM - 2); c.lineTo(x, HM); c.stroke(); }
            c.fillStyle = mix(th.bois, '#ffffff', .15); c.fillRect(0, HM - 2.08, L, .1);
          } else if (p === 5) {        // tasseaux bois pleine hauteur à gauche, panneaux sombres à droite, poutre haute
            if (type === 'g') { for (let x = .1; x < L; x += .32) { c.fillStyle = mix(th.bois, '#000000', .35 + alea(Math.round(x * 10), 7) * .1); c.fillRect(x, .5, .18, HM - .5); } }
            else { c.strokeStyle = 'rgba(255,255,255,.05)'; c.lineWidth = px * 1.2; for (let x = 1; x < L; x += 2) c.strokeRect(x - .9, .9, 1.8, HM - 1.4); }
            c.fillStyle = '#1a1612'; c.fillRect(0, 0, L, .5);
          }
          if (p !== 5) { c.fillStyle = p === 1 ? '#7d776d' : mix(th.bois, '#ffffff', p === 2 ? .45 : .1); c.fillRect(0, HM - .36, L, .36); c.fillStyle = 'rgba(0,0,0,.18)'; c.fillRect(0, HM - .38, L, .04); }
        });
      }
      // arête du coin et dessus des murs
      poly(c, [iso(0, 0, 0), iso(0, 0, HM)], null, 'rgba(0,0,0,.25)', 1);
      poly(c, [iso(0, 0, HM), iso(W, 0, HM), iso(W, -.15, HM), iso(-.15, -.15, HM), iso(-.15, H, HM), iso(0, H, HM)], p === 5 ? '#2a241e' : mix(th.mur, '#ffffff', .3), 'rgba(0,0,0,.25)');
    }

    // -------- fenêtre et vue (dessinée à chaque image : nuages, eau, étoiles bougent)
    function vue(c, w, h, th, px, t) {
      const [c1, c2] = G.ciel(), nuit = G.nuit();
      const g = c.createLinearGradient(0, 0, 0, h); g.addColorStop(0, c1); g.addColorStop(1, c2); c.fillStyle = g; c.fillRect(0, 0, w, h);
      const v = th.vue, sil = nuit ? '#141826' : null;
      if (v === 'espace' || nuit) for (let i = 0; i < 26; i++) { c.fillStyle = `rgba(255,255,240,${.4 + .5 * Math.sin(t * 2 + i * 3.1) ** 2})`; c.fillRect(alea(i, 1) * w, alea(i, 2) * h * .7, px * 1.6, px * 1.6); }
      if (v === 'espace') { c.fillStyle = mix(th.accent2, '#ffffff', .2); c.beginPath(); c.arc(w * .7, h * .35, h * .16, 0, 7); c.fill(); c.strokeStyle = rgba('#ffffff', .5); c.lineWidth = px * 1.5; c.beginPath(); c.ellipse(w * .7, h * .35, h * .28, h * .06, -.3, 0, 7); c.stroke(); return; }
      if (v === 'souterrain') { c.fillStyle = '#2a2420'; c.fillRect(0, 0, w, h); for (let i = 0; i < 7; i++) { c.fillStyle = rgba(th.accent2, .5 + .3 * Math.sin(t + i)); c.beginPath(); const x = alea(i, 4) * w, y = h * (.5 + alea(i, 5) * .45); c.moveTo(x, y); c.lineTo(x + .08, y - .5); c.lineTo(x + .16, y); c.fill(); } return; }
      if (!nuit) for (let i = 0; i < 3; i++) { const x = ((t * .04 + alea(i, 7)) % 1.3) * w * 1.1 - w * .15, y = h * (.12 + i * .12); c.fillStyle = 'rgba(255,255,255,.75)'; c.beginPath(); c.ellipse(x, y, w * .12, h * .05, 0, 0, 7); c.ellipse(x + w * .07, y - h * .03, w * .08, h * .05, 0, 0, 7); c.fill(); }
      const sol = (coul, f) => { c.fillStyle = sil || coul; c.beginPath(); c.moveTo(0, h); for (let x = 0; x <= w + .01; x += w / 24) c.lineTo(x, f(x)); c.lineTo(w, h); c.closePath(); c.fill(); };
      if (v === 'montagne') { sol('#8aa0b8', x => h * (.45 + .25 * Math.abs(Math.sin(x * 1.7)))); c.fillStyle = nuit ? '#2b3040' : '#f4f7fb'; for (let i = 0; i < 3; i++) { const x = (i + .5) * w / 3; c.beginPath(); c.moveTo(x - .25, h * .5); c.lineTo(x, h * .42); c.lineTo(x + .25, h * .5); c.fill(); } sol('#5f7a5a', x => h * (.75 + .06 * Math.sin(x * 3))); }
      else if (v === 'desert') { c.fillStyle = nuit ? '#e8e6d8' : '#ffd36b'; c.beginPath(); c.arc(w * .75, h * .3, h * .08, 0, 7); c.fill(); sol('#e2b46e', x => h * (.65 + .08 * Math.sin(x * 2.2))); sol('#c8955a', x => h * (.8 + .06 * Math.sin(x * 3 + 1))); c.fillStyle = sil || '#4f7a4a'; c.fillRect(w * .25, h * .58, .08, h * .25); c.fillRect(w * .25 - .14, h * .64, .08, h * .1); c.fillRect(w * .25 - .14, h * .7, .2, .06); }
      else if (v === 'mer' || v === 'tropical') { c.fillStyle = nuit ? '#1c2a44' : '#3f86b8'; c.fillRect(0, h * .62, w, h * .38); c.strokeStyle = 'rgba(255,255,255,.55)'; c.lineWidth = px * 1.2; for (let i = 0; i < 8; i++) { const x = (alea(i, 3) * w + t * .05 * (1 + i % 3)) % w, y = h * (.68 + alea(i, 4) * .28); c.beginPath(); c.moveTo(x, y); c.lineTo(x + .12, y); c.stroke(); } if (v === 'tropical') { c.fillStyle = sil || '#2f5a34'; c.fillRect(w * .2, h * .35, .07, h * .5); for (let i = 0; i < 5; i++) { c.beginPath(); c.ellipse(w * .2 + .03, h * .35, .32, .07, -1 + i * .5, 0, 7); c.fill(); } } else { c.fillStyle = sil || '#f4ecd9'; const x = (t * .03 % 1.4) * w - .2; c.beginPath(); c.moveTo(x, h * .62); c.lineTo(x + .1, h * .42); c.lineTo(x + .2, h * .62); c.fill(); } }
      else if (v === 'ville') { for (let i = 0; i < 9; i++) { const x = i * w / 9, hh = h * (.25 + alea(i, 2) * .4); c.fillStyle = sil || mix('#5b6478', '#000000', alea(i, 1) * .3); c.fillRect(x, h - hh, w / 9 - .03, hh); c.fillStyle = nuit ? 'rgba(255,214,120,.8)' : 'rgba(220,235,255,.5)'; for (let k = 0; k < 6; k++) if (alea(i, k + 10) > .45) c.fillRect(x + .04 + (k % 2) * .12, h - hh + .15 + Math.floor(k / 2) * .3, .06, .1); } }
      else if (v === 'imaginaire') { for (let i = 0; i < 3; i++) { const x = w * (.2 + i * .3), y = h * (.4 + .1 * Math.sin(t * .6 + i * 2)); c.fillStyle = sil || '#7aa86a'; c.beginPath(); c.ellipse(x, y, .3, .06, 0, Math.PI, 0); c.fill(); c.fillStyle = sil || '#8a6a4a'; c.beginPath(); c.moveTo(x - .3, y); c.lineTo(x, y + .35); c.lineTo(x + .3, y); c.fill(); } }
      else { sol('#7f9f6a', x => h * (.62 + .07 * Math.sin(x * 2.4))); if (v === 'foret' || v === 'campagne') for (let i = 0; i < (v === 'foret' ? 11 : 4); i++) { const x = alea(i, 6) * w, y = h * (.62 + alea(i, 8) * .2); c.fillStyle = sil || mix('#3f6a40', '#1d3a22', alea(i, 9)); c.beginPath(); c.moveTo(x - .15, y + .3); c.lineTo(x, y - .35); c.lineTo(x + .15, y + .3); c.fill(); } sol('#6a8a56', x => h * (.86 + .04 * Math.sin(x * 4))); }
    }
    function fenetre(c, th, p, t) {
      if (p === 5) {               // verrière
        const a = 5.0, b = 8.8, z0 = .3, z1 = 5.5;
        plan(c, 'g', 0, a, z1, (c, px) => { vue(c, b - a, z1 - z0, th, px, t); c.strokeStyle = '#1a1612'; c.lineWidth = px * 4; c.strokeRect(0, 0, b - a, z1 - z0); c.lineWidth = px * 2.2; for (let x = (b - a) / 4; x < b - a - .01; x += (b - a) / 4) { c.beginPath(); c.moveTo(x, 0); c.lineTo(x, z1 - z0); c.stroke(); } for (let y = (z1 - z0) / 4; y < z1 - z0 - .01; y += (z1 - z0) / 4) { c.beginPath(); c.moveTo(0, y); c.lineTo(b - a, y); c.stroke(); } const g = c.createLinearGradient(0, 0, b - a, z1 - z0); g.addColorStop(0, 'rgba(255,255,255,.14)'); g.addColorStop(.5, 'rgba(255,255,255,0)'); c.fillStyle = g; c.fillRect(0, 0, b - a, z1 - z0); });
        return;
      }
      const [a, b, z0, z1] = p === 1 ? [5.7, 7.3, 2.5, 4.1] : [5.4, 7.6, 1.8, 4.4];
      plan(c, 'g', 0, a, z1, (c, px) => {
        vue(c, b - a, z1 - z0, th, px, t);
        const cad = p === 1 ? '#5a5650' : p >= 4 ? '#2a241e' : mix(th.bois, '#ffffff', .5);
        c.strokeStyle = cad; c.lineWidth = px * 4; c.strokeRect(0, 0, b - a, z1 - z0); c.lineWidth = px * 2; c.beginPath(); c.moveTo((b - a) / 2, 0); c.lineTo((b - a) / 2, z1 - z0); if (p === 1) { c.moveTo(0, (z1 - z0) / 2); c.lineTo(b - a, (z1 - z0) / 2); } c.stroke();
        const g = c.createLinearGradient(0, 0, b - a, z1 - z0); g.addColorStop(0, 'rgba(255,255,255,.18)'); g.addColorStop(.4, 'rgba(255,255,255,0)'); c.fillStyle = g; c.fillRect(0, 0, b - a, z1 - z0);
        c.fillStyle = mix(cad, '#000000', .2); c.fillRect(-.1, z1 - z0, b - a + .2, .18);   // appui
      });
      if (p === 1) plante(c, th, .25, 6.55, 0, .45, .2, z0Appui());
      function z0Appui() { return 2.5; }
    }
    function lumiereFenetre(p) { return p === 5 ? [5.0, 8.8, .3, 5.5] : p === 1 ? [5.7, 7.3, 2.5, 4.1] : [5.4, 7.6, 1.8, 4.4]; }

    // -------- objets
    function plante(c, th, gx, gy, k, taille, potH, z0 = 0) {
      const t = now(), s = taille || 1, sorte = th.plante;
      boite(c, gx - .2 * s, gy - .2 * s, .4 * s, .4 * s, (potH || .6) * s, mix(th.accent2, '#7a4a30', .5), z0, { ombre: !z0 });
      const [x, y] = iso(gx, gy, z0 + (potH || .6) * s), TW = G.TW(), u = TW * s, vent = Math.sin(t * .9 + gx) * .04;
      c.save(); c.translate(x, y);
      if (sorte === 'cactus') { c.fillStyle = '#4f8a52'; c.beginPath(); c.roundRect ? c.roundRect(-u * .07, -u * .55, u * .14, u * .55, u * .07) : c.rect(-u * .07, -u * .55, u * .14, u * .55); c.fill(); c.fillRect(-u * .2, -u * .38, u * .13, u * .06); c.fillRect(-u * .2, -u * .48, u * .06, u * .14); c.fillStyle = '#f2b7a6'; c.beginPath(); c.arc(0, -u * .56, u * .04, 0, 7); c.fill(); }
      else if (sorte === 'cristal') { [-.08, .04, .12].forEach((dx, i) => { c.fillStyle = rgba(mix(th.accent2, '#ffffff', i * .2), .85); c.beginPath(); c.moveTo(u * dx - u * .05, 0); c.lineTo(u * dx, -u * (.35 + i * .1)); c.lineTo(u * dx + u * .05, 0); c.fill(); }); }
      else if (sorte === 'champignon') { c.fillStyle = '#efe6d2'; c.fillRect(-u * .03, -u * .25, u * .06, u * .25); c.fillStyle = mix(th.accent, '#a8432e', .4); c.beginPath(); c.ellipse(0, -u * .26, u * .16, u * .09, 0, Math.PI, 0); c.fill(); }
      else { const n = sorte === 'palmier' ? 6 : 9; for (let i = 0; i < n; i++) { const a = -Math.PI / 2 + (i - (n - 1) / 2) * (sorte === 'palmier' ? .45 : .32) + vent; c.fillStyle = mix('#3f7a52', '#7fae5e', (i % 3) / 3); c.beginPath(); c.ellipse(Math.cos(a) * u * .2, -u * .12 + Math.sin(a) * u * .22, u * (sorte === 'palmier' ? .2 : .12), u * .055, a, 0, 7); c.fill(); } }
      c.restore();
    }
    function chaiseBureau(c, gx, gy, coul, dos, p) {
      const [x, y] = iso(gx, gy, 0), TW = G.TW();
      if (!dos) { c.fillStyle = '#2b2620'; c.fillRect(x - 1, y - TW * .3, 2, TW * .3); c.strokeStyle = '#2b2620'; c.lineWidth = 2; c.beginPath(); c.moveTo(x - TW * .12, y + 1); c.lineTo(x + TW * .12, y - 1); c.moveTo(x - TW * .08, y - 2); c.lineTo(x + TW * .08, y + 2); c.stroke(); boite(c, gx - .2, gy - .2, .4, .4, .1, coul, .62, { ombre: false }); }
      else if (p >= 2) boite(c, gx - .2, gy + .18, .4, .06, .7, coul, .8, { ombre: false });
      else boite(c, gx - .2, gy + .18, .4, .05, .5, coul, .8, { ombre: false });
    }
    // Bureau d'un poste (appelé par la page) : le personnage est assis au point (sx + .55, sy + .47), dos à nous.
    function bureau(c, sx, sy, th, p, occupe, dessineAssis) {
      const t = now(), TW = G.TW(), Hb = 1.36, bx = sx - .15, by = sy - .6, bw = 1.5, bd = .75;
      const plateau = p === 1 ? mix('#c9a477', th.bois, .3) : p === 2 ? mix(th.bois, '#ffffff', .15) : p === 3 ? '#e9e4da' : p === 4 ? mix(th.bois, '#000000', .05) : '#2a2622';
      if (p === 1) { [[bx + .15, by + .1], [bx + bw - .3, by + .1]].forEach(([x, y]) => { boite(c, x, y, .1, .55, Hb - .08, '#8a6a48'); }); }
      else if (p <= 3) { boite(c, bx + .05, by + .05, .1, bd - .1, Hb - .08, p === 3 ? '#cfc8bb' : mix(plateau, '#000000', .2)); boite(c, bx + bw - .15, by + .05, .1, bd - .1, Hb - .08, p === 3 ? '#cfc8bb' : mix(plateau, '#000000', .2)); if (p === 2) boite(c, bx + bw - .55, by + .05, .4, bd - .1, Hb - .1, mix(plateau, '#000000', .1)); }
      else { boite(c, bx + .05, by + .05, bw - .1, bd - .1, Hb - .08, p === 5 ? '#1e1b18' : mix(plateau, '#000000', .25)); if (p === 5) { const [x0, y0] = iso(bx + .05, by + bd - .05, .1), [x1, y1] = iso(bx + bw - .05, by + bd - .05, .1); c.strokeStyle = rgba(th.accent, .6 + .2 * Math.sin(t * 2)); c.lineWidth = 2; c.beginPath(); c.moveTo(x0, y0); c.lineTo(x1, y1); c.stroke(); } }
      boite(c, bx, by, bw, bd, .08, plateau, Hb - .08, { ombre: false });
      // écran(s) : face vers nous
      const ecrans = p >= 4 ? [[sx + .02, .62], [sx + .7, .62]] : p === 3 ? [[sx + .1, .5], [sx + .7, .5]] : [[sx + .15, .8]];
      for (const [ex, ew] of ecrans) {
        const ez = Hb + .12, eh = p === 1 ? .78 : .72;
        if (p === 1) boite(c, ex + .1, by + .12, ew - .2, .3, .55, '#d8d0bf', Hb, { ombre: false });   // vieil écran épais
        else boite(c, ex + ew / 2 - .04, by + .2, .08, .08, .14, '#3a3a40', Hb, { ombre: false });
        boite(c, ex, by + .2, ew, .05, eh, p === 1 ? '#cfc6b4' : '#24262c', ez, { ombre: false });
        plan(c, 'd', by + .25, ex + .05, ez + eh - .06, (c, px) => {
          const w = ew - .1, h = eh - .12;
          if (occupe) {
            c.fillStyle = p === 1 ? '#1f2b22' : '#1d2230'; c.fillRect(0, 0, w, h);
            for (let i = 0; i < 6; i++) { const l = (alea(i, Math.floor(t * 1.5 + ex * 7)) * .7 + .2) * w; c.fillStyle = [th.accent, '#9fd29a', '#8fb0d6', '#e8dcc2'][i % 4]; c.globalAlpha = .85; c.fillRect(.04 + (i % 3) * .03, .05 + i * h / 7, l - .08, px * 2.2); }
            c.globalAlpha = 1; if (Math.sin(t * 6) > 0) { c.fillStyle = '#e8dcc2'; c.fillRect(.08, .05 + 6 * h / 7, px * 3, px * 3); }
          } else { c.fillStyle = '#15171c'; c.fillRect(0, 0, w, h); c.fillStyle = 'rgba(255,255,255,.06)'; c.fillRect(0, 0, w * .4, h); }
        });
      }
      // clavier, tasse, petits objets
      boite(c, sx + .3, sy - .1, .5, .16, .025, '#3a3a42', Hb, { ombre: false });
      boite(c, sx + 1.05, sy - .4, .12, .12, .14, p >= 3 ? th.accent : '#f4ecd9', Hb, { ombre: false });
      if (p >= 2) { const [x, y] = iso(sx - .02, sy - .45, Hb); c.fillStyle = '#3f7a52'; c.beginPath(); c.ellipse(x, y - TW * .08, TW * .07, TW * .05, 0, 0, 7); c.fill(); }
      // chaise : assise, personnage, dossier devant (il nous tourne le dos)
      const cx0 = sx + .55, cy0 = sy + .47, coul = p === 1 ? '#5a4f45' : p >= 4 ? mix(th.accent2, '#202020', .45) : '#3a3a42';
      if (occupe) { chaiseBureau(c, cx0, cy0, coul, false, p); dessineAssis(cx0, cy0); chaiseBureau(c, cx0, cy0, coul, true, p); }
      else { chaiseBureau(c, cx0, cy0 + .1, coul, false, p); chaiseBureau(c, cx0, cy0 + .1, coul, true, p); }
    }

    // Mobilier par palier : { de, a, gx, gy (ancre, sert au tri et à l'apparition), mur (dessiné avec les murs), f }
    const MOBILIER = [
      // ---- garage (1) : joli dès le départ
      { id: 'guirlande', de: 1, a: 2, mur: true, f(c, th, p, t) { const pts = []; for (let i = 0; i <= 22; i++) { const gy = .4 + i * .5, z = 5.35 - .25 * Math.abs(Math.sin(i * Math.PI / 4)); pts.push([gy, z]); } c.strokeStyle = '#3a3128'; c.lineWidth = 1; c.beginPath(); pts.forEach(([gy, z], i) => { const [x, y] = iso(0, gy, z); i ? c.lineTo(x, y) : c.moveTo(x, y); }); c.stroke(); pts.forEach(([gy, z], i) => { const [x, y] = iso(0, gy, z - .1), a = .55 + .45 * Math.sin(t * 2.2 + i * 1.7); c.fillStyle = rgba(['#ffd27a', '#ffb36b', '#fff0c0'][i % 3], a); c.beginPath(); c.arc(x, y, G.TW() * .035, 0, 7); c.fill(); }); } },
      { id: 'radiateur', de: 1, a: 3, mur: true, f(c) { plan(c, 'g', 0, 2.2, 1.2, (c, px) => { c.fillStyle = '#d8d2c6'; c.fillRect(0, 0, 1.6, .85); c.strokeStyle = 'rgba(0,0,0,.18)'; c.lineWidth = px * 1.4; for (let x = .12; x < 1.6; x += .16) { c.beginPath(); c.moveTo(x, .05); c.lineTo(x, .8); c.stroke(); } }); } },
      { id: 'etagere_metal', de: 1, a: 2, gx: 15.4, gy: 5.6, f(c, th) { [0, .8, 1.6, 2.4].forEach(z => boite(c, 15.15, 4.9, .55, 1.4, .06, '#8a8a88', z, { ombre: z === 0 })); [[4.95, 0], [6.25, 0]].forEach(([y]) => boite(c, 15.15, y, .06, .06, 2.5, '#6a6a68', 0, { ombre: false })); [[5.0, .06, '#c94f3a'], [5.5, .06, '#4d6f9c'], [5.1, .86, '#e2b866'], [5.7, .86, '#8a8174'], [5.3, 1.66, '#b08850']].forEach(([y, z, col]) => boite(c, 15.22, y, .38, .32, .5, col, z, { ombre: false })); } },
      { id: 'cartons', de: 1, a: 2, gx: 14.6, gy: 10.7, f(c) { boite(c, 14.1, 10.3, .8, .7, .7, '#b08850'); boite(c, 14.2, 10.4, .6, .55, .55, '#c49a62', .7, { ombre: false }); boite(c, 15.0, 10.6, .55, .55, .5, '#a07a48'); const [x, y] = iso(14.5, 10.3, .7); c.fillStyle = 'rgba(255,255,255,.35)'; c.fillRect(x - 1, y + 2, 2, 9); } },
      { id: 'ventilo', de: 1, a: 2, gx: 12.9, gy: 9.9, f(c, th, p, t) { boite(c, 12.75, 9.75, .3, .3, .06, '#3a3a40'); const [x, y] = iso(12.9, 9.9, 0), [hx, hy] = iso(12.9, 9.9, 1.3), TW = G.TW(); c.strokeStyle = '#3a3a40'; c.lineWidth = 2; c.beginPath(); c.moveTo(x, y); c.lineTo(hx, hy); c.stroke(); c.save(); c.translate(hx, hy); c.fillStyle = 'rgba(200,200,205,.35)'; c.beginPath(); c.arc(0, 0, TW * .2, 0, 7); c.fill(); c.rotate(t * 14); c.fillStyle = 'rgba(80,90,100,.75)'; for (let i = 0; i < 3; i++) { c.rotate(2.094); c.beginPath(); c.ellipse(TW * .1, 0, TW * .09, TW * .04, 0, 0, 7); c.fill(); } c.restore(); c.strokeStyle = 'rgba(60,60,65,.6)'; c.lineWidth = 1; c.beginPath(); c.arc(hx, hy, TW * .2, 0, 7); c.stroke(); } },
      { id: 'chat', de: 1, gx: 11.2, gy: 11.4, f(c, th, p, t) { const [cgx, cgy] = p >= 4 ? [10.9, 11.5] : [12.6, 11.3], [x, y] = iso(cgx, cgy, 0), TW = G.TW(), r = 1 + .04 * Math.sin(t * 1.6); ellipseSol(c, cgx, cgy, .42, .32, mix(th.accent2, '#3a3028', .3)); c.save(); c.translate(x, y - TW * .06); c.fillStyle = '#e09a4a'; c.beginPath(); c.ellipse(0, 0, TW * .17 * r, TW * .1 * r, -.15, 0, 7); c.fill(); c.beginPath(); c.arc(TW * .14, -TW * .04, TW * .07, 0, 7); c.fill(); c.beginPath(); c.moveTo(TW * .1, -TW * .09); c.lineTo(TW * .12, -TW * .15); c.lineTo(TW * .15, -TW * .1); c.moveTo(TW * .16, -TW * .09); c.lineTo(TW * .2, -TW * .14); c.lineTo(TW * .2, -TW * .07); c.fill(); c.strokeStyle = '#e09a4a'; c.lineWidth = TW * .035; c.lineCap = 'round'; c.beginPath(); c.moveTo(-TW * .15, TW * .02); c.quadraticCurveTo(-TW * .22, TW * .08 + Math.sin(t * .7) * TW * .03, -TW * .05, TW * .09); c.stroke(); c.strokeStyle = '#b06a2a'; c.lineWidth = 1; c.beginPath(); c.moveTo(-TW * .05, -TW * .08); c.lineTo(-TW * .02, TW * .06); c.moveTo(.0, -TW * .09); c.lineTo(TW * .03, TW * .06); c.stroke(); c.restore(); if (Math.sin(t * .4) > .7) { c.fillStyle = 'rgba(255,255,255,.7)'; c.font = `${Math.round(TW * .14)}px sans-serif`; c.fillText('z', x + TW * .22, y - TW * .3 - (t % 2) * 4); } } },
      { id: 'ampoule', de: 1, a: 1, gx: 7.6, gy: 5.6, lumiere: 'ampoule', f(c, th, p, t) { const s = Math.sin(t * .8) * .12, [x0, y0] = iso(7.6, 5.6, HM + .3), [x, y] = iso(7.6 + s, 5.6 - s, 5.1); c.strokeStyle = '#2b2620'; c.lineWidth = 1.2; c.beginPath(); c.moveTo(x0, y0); c.lineTo(x, y); c.stroke(); const TW = G.TW(), g = c.createRadialGradient(x, y + TW * .06, 0, x, y + TW * .06, TW * .5); g.addColorStop(0, rgba(th.lumiere, .55)); g.addColorStop(1, rgba(th.lumiere, 0)); c.fillStyle = g; c.beginPath(); c.arc(x, y + TW * .06, TW * .5, 0, 7); c.fill(); c.fillStyle = '#fff3c8'; c.beginPath(); c.ellipse(x, y + TW * .07, TW * .045, TW * .06, 0, 0, 7); c.fill(); c.fillStyle = '#3a3128'; c.fillRect(x - TW * .03, y - TW * .01, TW * .06, TW * .04); } },
      // ---- petit bureau (2)
      { id: 'plantes_coins', de: 2, gx: 15.3, gy: 11.2, f(c, th, p) { if (p === 3) plante(c, th, 15.3, 11.2, 0, 1.3, .6);   // coin : cartons au petit bureau, salle de réunion dès le studio pro
        plante(c, th, .6, 11.3, 0, 1.3, .6); } },
      { id: 'plante_porte', de: 2, gx: .7, gy: 8.3, f(c, th) { plante(c, th, .7, 8.3, 0, 1.6, .5); } },
      { id: 'tableau_blanc', de: 2, a: 3, gx: 15.1, gy: 8.3, f(c, th) { boite(c, 15.05, 7.75, .08, .08, 2.6, '#8a8a88'); boite(c, 15.05, 8.95, .08, .08, 2.6, '#8a8a88'); plan(c, 'g', 15.14, 7.7, 2.8, (c, px) => { c.fillStyle = '#f7f7f2'; c.fillRect(0, 0, 1.4, 1.9); c.strokeStyle = '#b8b8b2'; c.lineWidth = px * 3; c.strokeRect(0, 0, 1.4, 1.9); c.lineWidth = px * 1.6; [[th.accent2, .3], ['#c2533c', .7], ['#3f7a52', 1.1]].forEach(([col, y], i) => { c.strokeStyle = col; c.beginPath(); c.moveTo(.15, y); for (let x = .15; x < 1.2; x += .1) c.lineTo(x, y + Math.sin(x * 9 + i) * .05); c.stroke(); }); [['#f3d27a', .2], ['#a8d0a0', .55], ['#f2b7a6', .9]].forEach(([col, x]) => { c.fillStyle = col; c.fillRect(x, 1.35, .25, .3); }); }); } },
      { id: 'horloge', de: 2, mur: true, f(c, th, p) { const [x, y] = iso(0, 8.3, 4.7), TW = G.TW(), r = TW * .2, d = new Date(); c.save(); c.translate(x, y); c.transform(1, -.5, 0, 1, 0, 0); c.fillStyle = p === 5 ? '#2a241e' : '#f4ecd9'; c.strokeStyle = '#3a3128'; c.lineWidth = 2; c.beginPath(); c.arc(0, 0, r, 0, 7); c.fill(); c.stroke(); c.strokeStyle = p === 5 ? th.accent : '#2b241c'; const aig = (a, l, w) => { c.lineWidth = w; c.beginPath(); c.moveTo(0, 0); c.lineTo(Math.sin(a) * l, -Math.cos(a) * l); c.stroke(); }; aig((d.getHours() % 12 + d.getMinutes() / 60) / 12 * 6.283, r * .5, 2); aig(d.getMinutes() / 60 * 6.283, r * .75, 1.4); c.strokeStyle = '#c2533c'; aig(d.getSeconds() / 60 * 6.283, r * .8, .8); c.restore(); } },
      // ---- studio (3)
      { id: 'ilot', de: 3, gx: 4.85, gy: 5.0, f(c, th, p) { const plat = p >= 4 ? mix(th.bois, '#000000', .05) : '#e9e4da'; boite(c, 4.05, 4.45, 1.6, 1.1, 1.28, p >= 4 ? mix(th.bois, '#000000', .3) : '#cfc8bb'); boite(c, 4.0, 4.4, 1.7, 1.2, .08, plat, 1.28, { ombre: false }); boite(c, 4.3, 4.6, .45, .3, .03, '#3a3a42', 1.36, { ombre: false }); boite(c, 4.9, 4.9, .5, .35, .02, '#f4ecd9', 1.36, { ombre: false }); boite(c, 5.15, 4.55, .12, .12, .14, th.accent, 1.36, { ombre: false }); [[5.95, 4.7], [5.95, 5.3]].forEach(([x, y]) => { boite(c, x - .15, y - .15, .3, .3, .06, th.accent2, .9, { ombre: false }); const [a, b] = iso(x, y, 0), [a2, b2] = iso(x, y, .9); c.strokeStyle = '#3a3a40'; c.lineWidth = 2; c.beginPath(); c.moveTo(a, b); c.lineTo(a2, b2); c.stroke(); }); } },
      { id: 'cafe', de: 3, gx: 15.3, gy: 5.3, f(c, th, p, t) { boite(c, 14.95, 4.55, .8, 1.35, 1.4, p >= 4 ? mix(th.bois, '#000000', .2) : '#cfc8bb'); boite(c, 14.9, 4.5, .9, 1.45, .08, p >= 4 ? '#2a2622' : '#efeae0', 1.4, { ombre: false }); boite(c, 15.05, 4.7, .5, .45, .75, '#3a3a42', 1.48, { ombre: false }); boite(c, 15.1, 4.75, .4, .1, .15, '#c0c0c8', 1.95, { ombre: false }); const [x, y] = iso(15.3, 5.1, 1.75), TW = G.TW(); c.fillStyle = rgba(th.accent2, .9); c.fillRect(x - 2, y - 1, 4, 3); boite(c, 15.2, 5.45, .14, .14, .14, '#f4ecd9', 1.48, { ombre: false }); boite(c, 15.45, 5.5, .14, .14, .14, th.accent, 1.48, { ombre: false }); const [sx, sy] = iso(15.27, 5.52, 1.7); for (let i = 0; i < 3; i++) { const k = (t * .5 + i / 3) % 1; c.fillStyle = `rgba(255,255,255,${.35 * (1 - k)})`; c.beginPath(); c.arc(sx + Math.sin(k * 6 + i) * 3, sy - k * TW * .4, TW * (.03 + k * .04), 0, 7); c.fill(); } } },
      { id: 'tele', de: 3, gx: 4.9, gy: 9.6, f(c, th, p, t) { boite(c, 4.05, 9.4, 1.7, .4, .55, p >= 4 ? mix(th.bois, '#000000', .25) : '#3a3a42'); boite(c, 4.75, 9.5, .3, .25, .08, '#1a1a1e', .55, { ombre: false }); const [lx, ly] = iso(4.95, 9.75, .6); c.fillStyle = Math.sin(t * 3) > 0 ? '#6fbf7f' : '#3a6a46'; c.fillRect(lx - 1, ly - 1, 2, 2); boite(c, 4.15, 9.48, 1.5, .06, .9, '#15161a', .7, { ombre: false }); plan(c, 'd', 9.54, 4.2, 1.55, (c, px) => { const w = 1.4, h = .8, k = t * .8; const g = c.createLinearGradient(0, 0, 0, h); g.addColorStop(0, mix(th.accent2, '#1d2230', .2)); g.addColorStop(1, mix(th.accent, '#1d2230', .3)); c.fillStyle = g; c.fillRect(0, 0, w, h); c.fillStyle = 'rgba(0,0,0,.35)'; for (let i = 0; i < 5; i++) { const x = ((i * .37 - k * .3) % 1.6 + 1.6) % 1.6 - .1; c.fillRect(x, h * .55, .18, h * .45); } c.fillStyle = '#f4ecd9'; const sx = .45 + Math.sin(k * 2) * .05, sy = h * .55 - Math.abs(Math.sin(k * 3)) * .25; c.fillRect(sx, sy - .14, .08, .14); }); } },
      { id: 'canape', de: 3, gx: 4.9, gy: 11.2, f(c, th, p) { const coul = mix(th.accent, '#4a3a30', .35); boite(c, 3.9, 10.8, 2.0, .7, .45, mix(coul, '#000000', .1)); boite(c, 3.95, 10.82, 1.9, .5, .38, mix(coul, '#ffffff', .08), .45, { ombre: false }); boite(c, 3.85, 10.8, .2, .7, .9, coul, 0, { ombre: false }); const qui = G.surCanape(); if (qui) G.dessinePerso(4.9, 11.0, qui, { anim: 'manette', ang: -Math.PI / 2, ombre: false }); boite(c, 3.9, 11.32, 2.0, .2, 1.55, coul, 0, { ombre: false }); boite(c, 5.75, 10.8, .2, .7, .9, coul, 0, { ombre: false }); boite(c, 4.2, 11.18, .35, .12, .3, th.accent2, .85, { ombre: false }); } },
      { id: 'affiches', de: 3, a: 4, mur: true, f(c, th) { [[9.15, th.accent, th.accent2], [10.0, th.accent2, '#f4ecd9']].forEach(([a, c1, c2], i) => plan(c, 'g', 0, a, 5.3, (c, px) => { c.fillStyle = '#2b241c'; c.fillRect(-.04, -.04, .78, 1.38); c.fillStyle = mix(c1, '#ffffff', .15); c.fillRect(0, 0, .7, 1.3); c.fillStyle = c2; c.beginPath(); if (i) { c.arc(.35, .5, .2, 0, 7); } else { c.moveTo(.1, 1.05); c.lineTo(.35, .45); c.lineTo(.6, 1.05); } c.fill(); c.fillStyle = 'rgba(0,0,0,.35)'; c.fillRect(.1, 1.12, .5, .06); })); } },
      { id: 'suspensions', de: 3, a: 4, lumiere: 'suspensions', f() {} },
      // ---- studio pro (4)
      { id: 'reunion', de: 4, gx: 14.2, gy: 10.3, f(c, th, p, t) {
        // ordre de dessin : parois vitrées du fond, chaises du fond, table, chaises de devant, arêtes hautes
        const verre = (pts) => { poly(c, pts, 'rgba(190,220,235,.16)', 'rgba(255,255,255,.35)'); };
        verre([iso(12.4, 8.6, 0), iso(16, 8.6, 0), iso(16, 8.6, 4.4), iso(12.4, 8.6, 4.4)]);
        verre([iso(12.4, 8.6, 0), iso(12.4, 12, 0), iso(12.4, 12, 4.4), iso(12.4, 8.6, 4.4)]);
        c.strokeStyle = '#2b2620'; c.lineWidth = 2; [[12.4, 8.6], [12.4, 12], [16, 8.6]].forEach(([x, y]) => { const [a, b] = iso(x, y, 0), [a2, b2] = iso(x, y, 4.4); c.beginPath(); c.moveTo(a, b); c.lineTo(a2, b2); c.stroke(); });
        const assise = mix(th.accent2, '#202020', .4), chaise = (x, y) => { boite(c, x - .04, y - .04, .08, .08, .7, '#2b2620', 0, { ombre: false }); ellipseSol(c, x, y, .22, .22, 'rgba(20,14,8,.18)'); boite(c, x - .2, y - .2, .4, .4, .1, assise, .7, { ombre: false }); };
        [[13.5, 9.7], [14.3, 9.7], [15.1, 9.7]].forEach(([x, y]) => chaise(x, y));
        boite(c, 14.15, 10.45, .3, .3, 1.2, '#3a3a40');
        boite(c, 13.15, 10.05, 2.3, 1.1, .08, p === 5 ? '#2a2622' : mix(th.bois, '#ffffff', .05), 1.2, { ombre: false });
        boite(c, 13.9, 10.3, .5, .35, .03, '#3a3a42', 1.28, { ombre: false });
        boite(c, 14.9, 10.4, .12, .12, .12, th.accent, 1.28, { ombre: false });
        [[13.5, 11.5], [14.3, 11.5], [15.1, 11.5]].forEach(([x, y]) => chaise(x, y));
        poly(c, [iso(12.4, 12, 4.4), iso(12.4, 8.6, 4.4), iso(16, 8.6, 4.4)], null, '#2b2620', 2);
        const [x, y] = iso(12.4, 9.6, 3.6); c.save(); c.translate(x, y); c.transform(1, -.5, 0, 1, 0, 0); c.fillStyle = 'rgba(255,255,255,.6)'; c.font = `600 ${Math.max(8, G.TW() * .13)}px sans-serif`; c.fillText(G.langue() === 'en' ? 'MEETING' : 'RÉUNION', 0, 0); c.restore();
      } },
      { id: 'ecrans_muraux', de: 4, mur: true, f(c, th, p, t) { [1.7, 2.75, 3.8].forEach((a, i) => plan(c, 'g', 0, a, 5.55, (c, px) => { c.fillStyle = '#15161a'; c.fillRect(-.05, -.05, 1.0, .95); c.fillStyle = '#1d2230'; c.fillRect(0, 0, .9, .85); if (i === 0) { for (let k = 0; k < 6; k++) { const h = (.2 + .55 * (.5 + .5 * Math.sin(t * .7 + k))) * .7; c.fillStyle = k % 2 ? th.accent : th.accent2; c.fillRect(.08 + k * .13, .78 - h, .08, h); } } else if (i === 1) { c.strokeStyle = '#9fd29a'; c.lineWidth = px * 2; c.beginPath(); for (let x = 0; x <= .8; x += .05) c.lineTo(.05 + x, .6 - .35 * (x / .8) - .06 * Math.sin(x * 12 + t)); c.stroke(); c.fillStyle = 'rgba(159,210,154,.15)'; c.lineTo(.85, .8); c.lineTo(.05, .8); c.fill(); } else { const g = c.createLinearGradient(0, 0, 0, .85); g.addColorStop(0, mix(th.accent2, '#ffffff', .2)); g.addColorStop(1, th.accent); c.fillStyle = g; c.fillRect(.05, .05, .8, .75); c.fillStyle = 'rgba(0,0,0,.4)'; c.beginPath(); c.moveTo(.05, .8); c.lineTo(.3, .4); c.lineTo(.5, .6); c.lineTo(.7, .3); c.lineTo(.85, .8); c.fill(); } })); } },
      { id: 'panneaux_acoustiques', de: 4, mur: true, f(c, th) { [[.3, 1.1], [11.5, 12.3], [12.5, 13.3], [13.5, 14.3], [14.5, 15.3]].forEach(([a, b], i) => plan(c, 'd', 0, a, 5.55, (c) => { c.fillStyle = mix(i % 2 ? th.accent : th.accent2, '#3a3028', .35); c.fillRect(0, 0, b - a, .9); c.fillStyle = 'rgba(255,255,255,.08)'; c.fillRect(0, 0, b - a, .12); })); } },
      { id: 'grande_plante', de: 4, gx: 11.9, gy: 11.4, f(c, th) { plante(c, th, 11.9, 11.4, 0, 2.2, .45); } },
      { id: 'appliques', de: 4, lumiere: 'appliques', mur: true, f(c, th) { [2.3, 6.5, 9.7].forEach(gx => { const [x, y] = iso(gx, 0, 4.3), TW = G.TW(); c.fillStyle = '#2b2620'; c.fillRect(x - TW * .05, y - TW * .02, TW * .1, TW * .08); const g = c.createRadialGradient(x, y - TW * .3, 0, x, y - TW * .3, TW * .9); g.addColorStop(0, rgba(th.lumiere, .28)); g.addColorStop(1, rgba(th.lumiere, 0)); c.fillStyle = g; c.beginPath(); c.ellipse(x, y - TW * .3, TW * .6, TW * .9, 0, 0, 7); c.fill(); }); } },
      // ---- studio AAA (5)
      { id: 'mezzanine', de: 5, gx: 2.0, gy: 1.2, f(c, th) { const z = 4.75, gc = '#2b2620'; /* fixée aux deux murs du coin, sans poteau : rien ne barre le tableau du mur */ boite(c, 0, 0, 4.55, 1.25, .25, '#3a3028', z - .25, { ombre: false }); boite(c, 0, 0, 4.55, 1.25, .02, mix(th.bois, '#000000', .2), z, { ombre: false }); plante(c, th, 3.6, .5, 0, 1, .4, z); boite(c, 1.2, .3, .6, .5, .35, th.accent, z, { ombre: false }); poly(c, [iso(0, 1.25, z), iso(4.55, 1.25, z), iso(4.55, 1.25, z + 1), iso(0, 1.25, z + 1)], 'rgba(190,220,235,.18)', 'rgba(255,255,255,.3)'); poly(c, [iso(4.55, 0, z), iso(4.55, 1.25, z), iso(4.55, 1.25, z + 1), iso(4.55, 0, z + 1)], 'rgba(190,220,235,.14)', 'rgba(255,255,255,.3)'); c.strokeStyle = gc; c.lineWidth = 2.2; c.beginPath(); let p0 = iso(0, 1.25, z + 1), p1 = iso(4.55, 1.25, z + 1), p2 = iso(4.55, 0, z + 1); c.moveTo(p0[0], p0[1]); c.lineTo(p1[0], p1[1]); c.lineTo(p2[0], p2[1]); c.stroke(); } },
      { id: 'borne_arcade', de: 5, gx: 15.5, gy: 6.6, f(c, th, p, t) { boite(c, 15.2, 6.3, .55, .6, 2.1, mix(th.accent2, '#1a1a22', .4)); boite(c, 15.15, 6.3, .1, .6, .35, '#1a1a22', 1.05, { ombre: false }); plan(c, 'g', 15.2, 6.35, 2.0, (c, px) => { c.fillStyle = '#0f1218'; c.fillRect(0, 0, .5, .55); for (let i = 0; i < 12; i++) { c.fillStyle = [th.accent, th.accent2, '#f4ecd9'][i % 3]; const x = (i * .13 + t * .2 * (1 + i % 2)) % .45, y = (alea(i, 2) * .45 + t * .1 * (i % 3)) % .5; c.fillRect(x + .02, y + .02, .04, .04); } }); const [x, y] = iso(15.2, 6.6, 2.15), TW = G.TW(); c.fillStyle = rgba(th.accent, .55 + .35 * Math.sin(t * 4)); c.fillRect(x - TW * .12, y - TW * .05, TW * .24, TW * .05); } },
      { id: 'trophees', de: 5, mur: true, f(c, th, p, t) { plan(c, 'g', 0, .2, 3.7, (c, px) => { c.fillStyle = '#2a241e'; c.fillRect(0, .55, 1.3, .07); c.fillRect(0, 1.25, 1.3, .07); [[.2, 0], [.65, 0], [1.0, .7], [.35, .7]].forEach(([x, y], i) => { c.fillStyle = i % 2 ? '#d9dde2' : '#e2b866'; c.beginPath(); c.moveTo(x - .1, y + .2); c.lineTo(x + .1, y + .2); c.lineTo(x + .06, y + .38); c.lineTo(x - .06, y + .38); c.fill(); c.fillRect(x - .02, y + .38, .04, .1); c.fillRect(x - .07, y + .46, .14, .07); }); c.fillStyle = `rgba(255,255,255,${.4 + .4 * Math.sin(t * 3)})`; c.fillRect(.17, .23, px * 3, px * 3); }); } },
      { id: 'neon', de: 5, mur: true, lumiere: 'neon', f(c, th, p, t) { const fl = Math.sin(t * 23) > .96 ? .4 : 1; plan(c, 'g', 0, 9.1, 5.3, (c, px) => { c.strokeStyle = rgba(th.accent, .25 * fl); c.lineWidth = px * 12; const forme = () => { c.beginPath(); c.moveTo(.2, .2); c.lineTo(1.2, .65); c.lineTo(.2, 1.1); c.closePath(); c.moveTo(1.35, .2); c.lineTo(1.35, 1.1); }; forme(); c.stroke(); c.strokeStyle = rgba(mix(th.accent, '#ffffff', .5), fl); c.lineWidth = px * 3; forme(); c.stroke(); }); } },
      { id: 'rails', de: 5, lumiere: 'rails', f() {} }
    ];

    // -------- lumière : voile d'ambiance, flaques de lumière, faisceau de fenêtre, poussière, particules
    function sources(th, p, t) {
      const l = [], ajoute = (gx, gy, r, f, coul) => l.push({ gx, gy, r, f, coul: coul || th.lumiere });
      const [a, b] = lumiereFenetre(p); const jour = !G.nuit();
      if (jour) ajoute(2.2, (a + b) / 2 + 1, p === 5 ? 4.2 : 2.6, p === 5 ? .85 : .6, '#fff6e0');
      if (p === 1) { const s = Math.sin(t * .8) * .12; ajoute(7.6 + s, 5.6 - s, 4.4, 1, th.lumiere); }
      if (p === 2) { ajoute(4.5, 5.2, 3.3, .8); ajoute(9.8, 5.2, 3.3, .8); }
      if (p === 3) { ajoute(4.85, 5.0, 2.8, .9); ajoute(8.6, 7.9, 3.2, .8); ajoute(4.9, 10.6, 2.6, .8); ajoute(15.2, 5.2, 2, .6); }
      if (p >= 4) { ajoute(4.85, 5.0, 2.8, .9); ajoute(8.6, 7.9, 3.4, .85); ajoute(4.9, 10.6, 2.6, .8); ajoute(14.2, 10.4, 2.4, .85); ajoute(15.2, 5.2, 2, .65); ajoute(12.6, 2.6, 2.4, .7); }
      if (p === 5) { for (let i = 0; i < 3; i++) { const k = t * .15 + i * 2.1; ajoute(8 + Math.sin(k) * 5, 6 + Math.cos(k * 1.3) * 3.5, 1.7, .55, i === 1 ? mix(th.accent, '#ffffff', .4) : th.lumiere); } ajoute(1.2, 9.8, 2, .5, th.accent); }
      for (const q of G.postesLumiere()) ajoute(q.gx, q.gy, p >= 3 ? 1.4 : 1.2, q.occupe ? .55 : .25, q.occupe ? '#cfe2ff' : th.lumiere);
      return l;
    }
    function eclairer(c, th, p, t) {
      const L = G.L(), DPR = G.DPR(), TW = G.TW();
      if (!ombreCv) ombreCv = document.createElement('canvas');
      if (ombreCv.width !== Math.round(L.w * DPR) || ombreCv.height !== Math.round(L.h * DPR)) { ombreCv.width = Math.round(L.w * DPR); ombreCv.height = Math.round(L.h * DPR); }
      const o = ombreCv.getContext('2d'); o.setTransform(DPR, 0, 0, DPR, 0, 0); o.globalCompositeOperation = 'source-over'; o.clearRect(0, 0, L.w, L.h);
      const nuit = G.nuit(), voile = clamp(th.ombre + (nuit ? .1 : 0) + (p === 1 ? .06 : p === 5 ? -.04 : 0), .05, .6);
      o.fillStyle = `rgba(14,10,22,${voile})`; o.fillRect(0, 0, L.w, L.h);
      const src = sources(th, p, t);
      o.globalCompositeOperation = 'destination-out';
      for (const s of src) { const [x, y] = iso(s.gx, s.gy, 0), r = s.r * TW * .62; o.save(); o.translate(x, y); o.scale(1, .55); const g = o.createRadialGradient(0, 0, 0, 0, 0, r * 1.9); g.addColorStop(0, `rgba(0,0,0,${.85 * s.f})`); g.addColorStop(1, 'rgba(0,0,0,0)'); o.fillStyle = g; o.beginPath(); o.arc(0, 0, r * 1.9, 0, 7); o.fill(); o.restore(); }
      // vignette douce
      o.globalCompositeOperation = 'source-over';
      const vg = o.createRadialGradient(L.w / 2, L.h * .55, Math.min(L.w, L.h) * .35, L.w / 2, L.h * .55, Math.max(L.w, L.h) * .75); vg.addColorStop(0, 'rgba(10,6,14,0)'); vg.addColorStop(1, `rgba(10,6,14,${.22 + voile * .3})`); o.fillStyle = vg; o.fillRect(0, 0, L.w, L.h);
      c.drawImage(ombreCv, 0, 0, L.w, L.h);
      // lumières additives (chaleur) et faisceau de la fenêtre
      c.save(); c.globalCompositeOperation = 'lighter';
      for (const s of src) { const [x, y] = iso(s.gx, s.gy, 0), r = s.r * TW * .5; c.save(); c.translate(x, y); c.scale(1, .55); const g = c.createRadialGradient(0, 0, 0, 0, 0, r * 1.5); g.addColorStop(0, rgba(s.coul, .1 * s.f)); g.addColorStop(1, rgba(s.coul, 0)); c.fillStyle = g; c.beginPath(); c.arc(0, 0, r * 1.5, 0, 7); c.fill(); c.restore(); }
      if (!nuit) {
        const [a, b, z0, z1] = lumiereFenetre(p), lg = p === 5 ? 5.2 : 3.4, pulse = p === 5 ? .7 + .3 * Math.sin(t * .4) : 1;
        const pts = [iso(0, a, z1), iso(0, b, z1), iso(lg, b + 1.4, 0), iso(lg, a + 1.4, 0)];
        const g = c.createLinearGradient(pts[0][0], pts[0][1], pts[2][0], pts[2][1]); g.addColorStop(0, `rgba(255,244,214,${.13 * pulse})`); g.addColorStop(1, 'rgba(255,244,214,0)');
        c.fillStyle = g; c.beginPath(); pts.forEach((q, i) => i ? c.lineTo(q[0], q[1]) : c.moveTo(q[0], q[1])); c.closePath(); c.fill();
        if (p === 5) for (let i = 0; i < 4; i++) { const k = (t * .05 + i * .27) % 1, gy = a + (b - a) * k; const q = [iso(0, gy, z1), iso(0, gy + .25, z1), iso(lg, gy + 1.65, 0), iso(lg, gy + 1.4, 0)]; c.fillStyle = 'rgba(255,240,200,.05)'; c.beginPath(); q.forEach((r, j) => j ? c.lineTo(r[0], r[1]) : c.moveTo(r[0], r[1])); c.closePath(); c.fill(); }
        // poussière dans le faisceau
        for (let i = 0; i < (p === 5 ? 34 : 18); i++) { const k = (t * (.02 + alea(i, 1) * .03) + alea(i, 2)) % 1, gx = .4 + alea(i, 3) * (lg - .6) * k + k * .3, gy = a + alea(i, 4) * (b - a) + k * 1.4, z = z1 * (1 - k) + Math.sin(t + i) * .2; const [x, y] = iso(gx, gy, z); c.fillStyle = `rgba(255,248,225,${.35 * Math.sin(k * Math.PI)})`; c.beginPath(); c.arc(x, y, 1.1, 0, 7); c.fill(); }
      }
      if (p === 5) for (let i = 0; i < 22; i++) { const k = (t * .03 + alea(i, 5)) % 1, gx = 1 + alea(i, 6) * 14, gy = 1 + alea(i, 7) * 10, z = k * 5; const [x, y] = iso(gx + Math.sin(t * .5 + i) * .3, gy, z); c.fillStyle = rgba(i % 2 ? th.accent : th.lumiere, .5 * Math.sin(k * Math.PI)); c.beginPath(); c.arc(x, y, 1.6, 0, 7); c.fill(); }
      c.restore();
      // suspensions (3-4) et rails (5) : par-dessus le voile, elles éclairent
      if (p === 3 || p === 4) [[4.85, 5.0], [8.6, 7.9], [4.9, 10.6], ...(p === 4 ? [[14.2, 10.4]] : [])].forEach(([gx, gy]) => suspension(c, th, gx, gy, p, t));
      if (p === 2) [[4.5, 5.2], [9.8, 5.2]].forEach(([gx, gy]) => suspension(c, th, gx, gy, p, t));
      if (p === 5) rails(c, th, t);
    }
    function suspension(c, th, gx, gy, p, t) {
      const TW = G.TW(), [x0, y0] = iso(gx, gy, HM + .3), [x, y] = iso(gx, gy, 5.4);
      c.strokeStyle = '#2b2620'; c.lineWidth = 1; c.beginPath(); c.moveTo(x0, y0); c.lineTo(x, y); c.stroke();
      const g = c.createRadialGradient(x, y + TW * .1, 0, x, y + TW * .1, TW * .55); g.addColorStop(0, rgba(th.lumiere, .45)); g.addColorStop(1, rgba(th.lumiere, 0)); c.fillStyle = g; c.beginPath(); c.arc(x, y + TW * .1, TW * .55, 0, 7); c.fill();
      c.fillStyle = p === 2 ? '#f4ecd9' : p === 4 ? mix(th.accent, '#2b2620', .3) : '#2b2f36';
      c.beginPath(); c.moveTo(x - TW * .03, y); c.lineTo(x + TW * .03, y); c.lineTo(x + TW * .14, y + TW * .1); c.lineTo(x - TW * .14, y + TW * .1); c.closePath(); c.fill();
      c.fillStyle = '#fff3c8'; c.beginPath(); c.ellipse(x, y + TW * .1, TW * .12, TW * .025, 0, 0, 7); c.fill();
    }
    function rails(c, th, t) {
      const TW = G.TW(); c.strokeStyle = 'rgba(26,22,18,.5)'; c.lineWidth = 1.5;   // rails fins : ils passent au-dessus des têtes
      [[2, 3.5, 14, 3.5], [2, 8.2, 14, 8.2]].forEach(([a, y, b]) => { const [x0, y0] = iso(a, y, 5.6), [x1, y1] = iso(b, y, 5.6); c.beginPath(); c.moveTo(x0, y0); c.lineTo(x1, y1); c.stroke(); for (let i = 0; i < 5; i++) { const k = ((i + .5) / 5 + Math.sin(t * .15 + i) * .03), [x, yy] = iso(a + (b - a) * k, y, 5.6); c.fillStyle = '#2b2620'; c.fillRect(x - TW * .04, yy, TW * .08, TW * .1); c.fillStyle = rgba(th.lumiere, .9); c.beginPath(); c.arc(x, yy + TW * .1, TW * .03, 0, 7); c.fill(); } });
    }

    // -------- chantier (passage de palier)
    function chantier(c, th, k, t) {
      const TW = G.TW();
      // échafaudage contre le mur du fond, plots, poussière, étincelles de perceuse
      const ech = clamp(k < .15 ? k / .15 : k > .85 ? (1 - k) / .15 : 1, 0, 1);
      c.save(); c.globalAlpha = ech;
      for (const gx of [6.2, 8.2, 10.2]) { const [a, b] = iso(gx, .6, 0), [a2, b2] = iso(gx, .6, 5.2); c.strokeStyle = '#c9953e'; c.lineWidth = 3; c.beginPath(); c.moveTo(a, b); c.lineTo(a2, b2); c.stroke(); }
      [1.8, 3.6].forEach(z => boite(c, 6.1, .45, 4.2, .35, .12, '#a0744a', z, { ombre: false }));
      [[7, 2.2], [9.5, 2.2], [12.5, 6.5]].forEach(([gx, gy]) => { const [x, y] = iso(gx, gy, 0); c.fillStyle = '#e8742c'; c.beginPath(); c.moveTo(x - TW * .1, y); c.lineTo(x, y - TW * .3); c.lineTo(x + TW * .1, y); c.fill(); c.fillStyle = '#fff'; c.fillRect(x - TW * .05, y - TW * .17, TW * .1, TW * .04); });
      c.restore();
      if (Math.random() < .5) { const [x, y] = iso(8.2 + (Math.random() - .5) * 3, .2, 2 + Math.random() * 2.5); for (let i = 0; i < 4; i++) ETINC.push({ x, y, vx: (Math.random() - .3) * 120, vy: -Math.random() * 90, v: 1 }); }
      if (Math.random() < .35) { const [x, y] = iso(1 + Math.random() * 14, 1 + Math.random() * 10, 0); POUSS.push({ x, y, r: TW * (.2 + Math.random() * .3), v: 1, vy: -10 - Math.random() * 15 }); }
      if (k > .42 && k < .5 && POUSS.length < 160) for (let i = 0; i < 20; i++) { const [x, y] = iso(Math.random() * W, Math.random() * H, Math.random() * 2); POUSS.push({ x, y, r: TW * (.5 + Math.random() * .8), v: 1, vy: -6 }); }
      // bandeau
      const L = G.L(), nom = (NOMS[G.langue()] || NOMS.fr)[etat.actuel - 1], txt = (G.langue() === 'en' ? 'Works in progress: ' : 'Travaux en cours : ') + nom;
      c.save(); c.globalAlpha = ech; c.font = '600 15px system-ui,sans-serif'; const w = c.measureText(txt).width + 60, x = L.w / 2 - w / 2, y = G.haut() + 14;
      c.fillStyle = '#2b241c'; c.fillRect(x, y, w, 30); c.save(); c.beginPath(); c.rect(x, y, w, 30); c.clip(); c.fillStyle = '#e8b53a'; for (let i = -2; i < w / 14 + 2; i++) { c.beginPath(); c.moveTo(x + i * 14 + (t * 20 % 14), y); c.lineTo(x + i * 14 + 7 + (t * 20 % 14), y); c.lineTo(x + i * 14 - 3 + (t * 20 % 14), y + 30); c.lineTo(x + i * 14 - 10 + (t * 20 % 14), y + 30); c.fill(); } c.restore();
      c.fillStyle = '#2b241c'; c.fillRect(x + 22, y + 4, w - 44, 22); c.fillStyle = '#f1d9a4'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(txt, L.w / 2, y + 15.5); c.restore();
    }
    function particules(c, dt) {
      for (let i = POUSS.length - 1; i >= 0; i--) { const q = POUSS[i]; q.v -= dt * .45; q.y += q.vy * dt; q.r *= 1 + dt * .25; if (q.v <= 0) { POUSS.splice(i, 1); continue; } c.fillStyle = `rgba(214,204,188,${.35 * q.v})`; c.beginPath(); c.arc(q.x, q.y, q.r, 0, 7); c.fill(); }
      for (let i = ETINC.length - 1; i >= 0; i--) { const q = ETINC[i]; q.v -= dt * 2.2; q.x += q.vx * dt; q.y += q.vy * dt; q.vy += 260 * dt; if (q.v <= 0) { ETINC.splice(i, 1); continue; } c.fillStyle = `rgba(255,${180 + Math.round(60 * q.v)},90,${q.v})`; c.fillRect(q.x, q.y, 2, 2); }
      void BRINS;
    }

    // -------- API pour la page
    let dernier = performance.now();
    function affiche() { if (etat.t0 && (performance.now() - etat.t0) / 1000 < DUREE * .47) return etat.ancien; return etat.actuel || 1; }
    function apparition(id, p) { const cle = p + ':' + id; if (!(cle in apparus)) apparus[cle] = etat.t0 && p === etat.actuel ? performance.now() + 120 * Object.keys(apparus).length % 1400 : 0; const t0 = apparus[cle]; if (!t0) return 1; const k = clamp((performance.now() - t0) / 550, 0, 1); return k <= 0 ? 0 : 1 + 2.4 * Math.pow(k - 1, 3) + 1.4 * Math.pow(k - 1, 2); }
    function dessinerItem(c, it, th, p, t) {
      const k = apparition(it.id, p); if (k <= 0) return;
      if (k !== 1 && it.gx != null) { const [x, y] = iso(it.gx, it.gy, 0); c.save(); c.translate(x, y); c.scale(k, k); c.translate(-x, -y); try { it.f(c, th, p, t); } finally { c.restore(); } }
      else it.f(c, th, p, t);
    }
    return {
      // p demandé ; anime = jouer le chantier si on monte
      regler(p, anime) {
        p = clamp(Math.round(p) || 1, 1, 5);
        if (p === etat.actuel) return false;
        const monte = etat.actuel && p > etat.actuel;
        if (anime && monte) { etat = { actuel: p, ancien: etat.actuel, t0: performance.now() }; apparus = {}; G.son('perceuse'); setTimeout(() => G.son('perceuse'), 1600); setTimeout(() => G.son('marteau'), 2900); setTimeout(() => G.son('fini'), DUREE * 1000 * .55); }
        else { etat = { actuel: p, ancien: p, t0: 0 }; }
        return monte;
      },
      palier: () => affiche(),
      cible: () => etat.actuel,
      enChantier: () => !!etat.t0 && (performance.now() - etat.t0) / 1000 < DUREE,
      // sol + murs (cache) puis éléments muraux et fenêtre (animés)
      fond(c, th) {
        const p = affiche(), t = now(), L = G.L(), DPR = G.DPR();
        const cle = [L.w, L.h, DPR, G.TW().toFixed(2), G.origine(), p, th.cle].join('|');
        if (cle !== cacheCle) {
          cache = cache || document.createElement('canvas'); cache.width = Math.round(L.w * DPR); cache.height = Math.round(L.h * DPR);
          const k = cache.getContext('2d'); k.setTransform(DPR, 0, 0, DPR, 0, 0); k.clearRect(0, 0, L.w, L.h); sol(k, th, p); murs(k, th, p); cacheCle = cle;
        }
        c.drawImage(cache, 0, 0, L.w, L.h);
        fenetre(c, th, p, t);
        for (const it of MOBILIER) if (it.mur && p >= it.de && p <= (it.a || 5)) { try { dessinerItem(c, it, th, p, t); } catch (e) { G.erreur('palier ' + it.id, e); } }
      },
      // mobilier au sol, trié avec les postes par la page
      objets(th, liste) {
        const p = affiche(), t = now();
        for (const it of MOBILIER) if (!it.mur && it.gx != null && p >= it.de && p <= (it.a || 5)) liste.push({ k: it.gx + it.gy, f: () => dessinerItem(G.cx(), it, th, p, t) });
      },
      bureau(c, sx, sy, th, occupe, dessineAssis) { bureau(c, sx, sy, th, affiche(), occupe, dessineAssis); },
      plante: (c, th, gx, gy, s) => plante(c, th, gx, gy, 0, s || 1, .6),
      // voile de lumière, particules, chantier (avant les étiquettes)
      lumiere(c, th) {
        const p = affiche(), t = now(), n = performance.now(), dt = Math.min(.1, (n - dernier) / 1000); dernier = n;
        try { eclairer(c, th, p, t); } catch (e) { G.erreur('éclairage', e); }
        if (etat.t0) { const k = (n - etat.t0) / 1000 / DUREE; if (k >= 1 && !POUSS.length) etat.t0 = 0; else if (k < 1) chantier(c, th, k, t); }
        particules(c, dt);
      }
    };
  }

  window.Paliers = { NOMS, calculer, theme, creer, mix };
})();
