/* studio/sprites.js : personnages rendus dans Blender (sprites/atlas.json), recolorés par masques.
   Une planche par (look, animation, direction, taille), teintée une fois puis gardée en cache.
   Tant que l'atlas ou une planche n'est pas chargé, dessine() renvoie null : la page garde son dessin vectoriel.
   Contrat des planches : sprites/LISEZMOI.md. Licence : MIT du skill (rendus faits pour le skill). */
(function () {
  'use strict';
  let ATLAS = null;
  const imgs = new Map(), lignes = new Map();
  const CACHE_MAX = 64 * 1024 * 1024; let cacheOctets = 0;   // O10 : toiles teintées gardées jusqu'à 64 Mo environ (4 octets par pixel)
  try {
    fetch('sprites/atlas.json', { cache: 'no-cache' }).then(r => r.ok ? r.json() : null).then(a => {
      if (!a || !a.anims) return; ATLAS = a;
      // O10 : précharge seulement les planches 128 de repos, marche, tape et portrait (base et masques) ; les autres se chargent
      // à la première demande et, en attendant, dessine() prend une animation proche déjà prête (tape ou repos), jamais le vectoriel
      for (const an of ['repos', 'marche', 'tape', 'portrait'].map(n => a.anims[n]).filter(Boolean)) for (const n of ['base', 'peau', 'cheveux', 'haut', 'bas', 'chaussures']) if (an.fichiers && an.fichiers[n]) img('sprites/' + an.fichiers[n].replace('{taille}', 128));
    }).catch(() => {});
  } catch (e) { /* pas de fetch : repli vectoriel */ }
  const hex = v => typeof v === 'string' && /^#[0-9a-f]{6}$/i.test(v);
  function mix(a, b, k) { const pa = parseInt(a.slice(1), 16), pb = parseInt(b.slice(1), 16); const c = i => Math.round(((pa >> i) & 255) + ((((pb >> i) & 255) - ((pa >> i) & 255)) * k)); return '#' + ((c(16) << 16) | (c(8) << 8) | c(0)).toString(16).padStart(6, '0'); }
  function img(chemin) { let i = imgs.get(chemin); if (!i) { i = new Image(); i.decoding = 'async'; i.src = chemin; imgs.set(chemin, i); } return i.complete && i.naturalWidth ? i : null; }
  function toile(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; }

  // Look de la page (peau, cheveux {coupe, couleur}, tenue {couleur1, couleur2, bas}, accessoire) -> couleurs des zones
  function couleurs(look) {
    look = look || {}; const tenue = look.tenue || {}, chev = look.cheveux || {};
    const peau = hex(look.peau) ? look.peau : '#f1c27d', haut = hex(tenue.couleur1) ? tenue.couleur1 : '#6b8f71';
    let cheveux = hex(chev.couleur) ? chev.couleur : '#2b1d14';
    if (chev.coupe === 'aucune') cheveux = mix(peau, '#000000', .08); else if (chev.coupe === 'rase') cheveux = mix(cheveux, peau, .55);
    const bas = hex(tenue.bas) ? tenue.bas : mix('#2c2f38', haut, .22);
    return { peau, cheveux, haut, bas, chaussures: hex(look.chaussures) ? look.chaussures : '#2a211b' };
  }
  // accessoire de la page -> [accessoire rendu, couleur] ; les autres sont dessinés en vectoriel par-dessus (voir surTete)
  function accessoire(look, C) {
    const a = (look && look.accessoire) || '';
    const t = { casque: ['casquette', '#e2b866'], casque_audio: ['casque_audio', '#3a3a42'], lunettes: ['lunettes', '#3a2c22'], beret: ['beret', '#a8432e'],
      casquette: ['casquette', mix(C.haut, '#000000', .25)], bonnet: ['bonnet', mix(C.haut, '#000000', .3)], barbe: ['barbe', C.cheveux] }[a];
    return t && ATLAS && ATLAS.accessoires.includes(t[0]) ? t : null;
  }
  function teinter(src, masques, d, T, n) {
    const w = n * T, cl = toile(w, T), g = cl.getContext('2d'); g.globalCompositeOperation = 'lighter';
    for (const [m, coul] of masques) { const t = toile(w, T), tg = t.getContext('2d'); tg.drawImage(m, 0, d * T, w, T, 0, 0, w, T); tg.globalCompositeOperation = 'source-in'; tg.fillStyle = coul; tg.fillRect(0, 0, w, T); g.drawImage(t, 0, 0); }
    const out = toile(w, T), o = out.getContext('2d');
    o.drawImage(src, 0, d * T, w, T, 0, 0, w, T); o.globalCompositeOperation = 'multiply'; o.drawImage(cl, 0, 0);
    o.globalCompositeOperation = 'destination-in'; o.drawImage(src, 0, d * T, w, T, 0, 0, w, T);
    o.globalCompositeOperation = 'source-over';
    return out;
  }
  function ligne(look, anim, d, T) {
    const a = ATLAS.anims[anim]; if (!a) return null;
    const C = couleurs(look), acc = accessoire(look, C);
    const cle = [anim, d, T, C.peau, C.cheveux, C.haut, C.bas, C.chaussures, acc ? acc.join('') : ''].join('|');
    const deja = lignes.get(cle); if (deja) { lignes.delete(cle); lignes.set(cle, deja); return deja; }   // la plus récente passe en fin de file
    const f = nom => a.fichiers[nom] && img('sprites/' + a.fichiers[nom].replace('{taille}', T));
    const base = f('base'), m = ['peau', 'cheveux', 'haut', 'bas', 'chaussures'].map(f);
    if (!base || m.some(x => !x)) return null;
    let ab = null, am = null; if (acc) { ab = f('acc_' + acc[0]); am = f('acc_' + acc[0] + '_masque'); if (!ab || !am) return null; }
    const corps = teinter(base, [[m[0], C.peau], [m[1], C.cheveux], [m[2], C.haut], [m[3], C.bas], [m[4], C.chaussures]], d, T, a.images);
    if (acc) corps.getContext('2d').drawImage(teinter(ab, [[am, acc[1]]], d, T, a.images), 0, 0);
    const oct = corps.width * corps.height * 4;
    while (lignes.size && (cacheOctets + oct > CACHE_MAX || lignes.size >= 160)) { const k0 = lignes.keys().next().value, v0 = lignes.get(k0); cacheOctets -= v0.width * v0.height * 4; lignes.delete(k0); }
    lignes.set(cle, corps); cacheOctets += oct; return corps;
  }
  const direction = ang => ((Math.round((ang || 0) / (Math.PI / 4)) % 8) + 8) % 8;

  // Accessoires sans rendu 3D : dessin vectoriel posé sur le haut de la tête (x, y en px écran, k = échelle).
  function surTete(c, look, x, y, k, C) {
    const a = (look && look.accessoire) || ''; if (!a) return;
    c.save(); c.translate(x, y); c.scale(k, k);
    switch (a) {
      case 'chapeau': c.fillStyle = '#4a3f33'; c.beginPath(); c.ellipse(0, 1, 11, 3.2, 0, 0, 7); c.fill(); c.fillStyle = '#5c4f3f'; c.fillRect(-6, -10, 12, 11); c.fillStyle = '#a8432e'; c.fillRect(-6, -2.5, 12, 2.2); break;
      case 'couronne': c.fillStyle = '#e2b866'; c.strokeStyle = '#8a5b12'; c.lineWidth = .8; c.beginPath(); c.moveTo(-7, 2); c.lineTo(-7, -6); c.lineTo(-3.5, -1.5); c.lineTo(0, -8); c.lineTo(3.5, -1.5); c.lineTo(7, -6); c.lineTo(7, 2); c.closePath(); c.fill(); c.stroke(); break;
      case 'bandeau': c.fillStyle = '#a8432e'; c.fillRect(-8, 3, 16, 2.6); break;
      case 'cornes': c.fillStyle = '#efe6d2'; c.beginPath(); c.moveTo(-6, 4); c.lineTo(-10, -6); c.lineTo(-3, 2); c.fill(); c.beginPath(); c.moveTo(6, 4); c.lineTo(10, -6); c.lineTo(3, 2); c.fill(); break;
      case 'capuche': c.strokeStyle = mix(C.haut, '#000000', .15); c.lineWidth = 3.2; c.beginPath(); c.arc(0, 8, 9.5, Math.PI * 1.05, Math.PI * 1.95); c.stroke(); break;
      default: break;
    }
    c.restore();
  }

  window.SpritesPerso = {
    pret: () => !!ATLAS,
    // q : { ang (0 = +x de la grille, π/2 = +y), anim ('repos', 'marche', 'tape'…), dist (marche), seed, ombre }
    // u : px écran par « px studio » de référence (TW = 64). Renvoie la hauteur du haut de la tête au-dessus des pieds (px écran), ou null.
    dessine(c, look, q, X, Y, u, dpr) {
      if (!ATLAS) return null;
      const d = direction(q.ang), veut = ATLAS.anims[q.anim] ? q.anim : 'repos';
      // planche pas encore chargée : une animation proche déjà prête (assis -> tape, debout -> repos) plutôt que le vectoriel
      const essais = [veut, ATLAS.anims[veut] && ATLAS.anims[veut].assis ? 'tape' : 'repos'];
      let an = null, a = null, T = 128, pl = null;
      for (const nom of essais) {
        const x = ATLAS.anims[nom]; if (!x) continue;
        const veut256 = (x.tailles || [128]).includes(256) && u * (dpr || 1) / 1.75 > 1.15;
        for (const t of veut256 ? [256, 128] : [128]) { pl = ligne(look, nom, d, t); if (pl) { an = nom; a = x; T = t; break; } }
        if (pl) break;
      }
      if (!pl) return null;
      const t = ATLAS.tailles[T], k = t.px_sprite_par_px_studio / u, ap = t.ancre_pieds;
      const f = an === 'marche' ? Math.floor((q.dist || 0) / ATLAS.marche.distance_par_cycle * a.images) % a.images
        : Math.floor((performance.now() / 1000 + (q.seed || 0)) * a.fps) % a.images;
      if (q.ombre !== false && !a.assis) { c.fillStyle = 'rgba(20,12,6,.24)'; c.beginPath(); c.ellipse(X, Y, 9.5 * u, 4 * u, 0, 0, 7); c.fill(); }
      c.drawImage(pl, f * T, 0, T, T, X - ap[0] / k, Y - ap[1] / k, T / k, T / k);
      const tt = a.ancres_256 && a.ancres_256.tete && a.ancres_256.tete[d] && a.ancres_256.tete[d][f];
      const h = tt ? (224 - tt[1]) / 3.5 * u : 44 * u;
      // mains du dernier perso dessiné (px écran) : l'hôte du studio y pose ce qu'il tient (tasse, livre, arrosoir…)
      const md = a.ancres_256 && a.ancres_256.mainD && a.ancres_256.mainD[d] && a.ancres_256.mainD[d][f], mg = a.ancres_256 && a.ancres_256.mainG && a.ancres_256.mainG[d] && a.ancres_256.mainG[d][f];
      const ecran = m => m ? [X + (m[0] - 128) / 3.5 * u, Y - (224 - m[1]) / 3.5 * u] : null;
      window.SpritesPerso.dernier = { mainD: ecran(md), mainG: ecran(mg), d, anim: an };
      if (tt) surTete(c, look, X + (tt[0] - 128) / 3.5 * u, Y - h, u * .62, couleurs(look));
      return h;
    },
    // cartes du groupe (DA 13/11) : médaillon « carnet » + buste rendu « portrait » (caméra à 11°, trois quarts) ; false si pas prêt
    buste(canvas, look) {
      const P0 = ATLAS && ATLAS.anims.portrait; if (!P0) return false;
      let pl = (P0.tailles || [128]).includes(256) ? ligne(look, 'portrait', 0, 256) : null; if (!pl) pl = ligne(look, 'portrait', 0, 128); if (!pl) return false;
      const s = pl.height / 256, r = P0.cadrage_256 || [14, 4, 228, 228], W = canvas.width, Hh = canvas.height, D = Math.min(W, Hh), x0 = (W - D) / 2, y0 = (Hh - D) / 2;
      const c = canvas.getContext('2d'), C = couleurs(look), rgbaH = (h, a) => `rgba(${parseInt(h.slice(1, 3), 16)},${parseInt(h.slice(3, 5), 16)},${parseInt(h.slice(5, 7), 16)},${a})`;
      c.clearRect(0, 0, W, Hh); c.save(); c.beginPath(); c.arc(W / 2, Hh / 2, D / 2, 0, 7); c.clip();
      const g0 = c.createRadialGradient(x0 + D * .38, y0 + D * .28, 1, x0 + D * .38, y0 + D * .28, D * .85); g0.addColorStop(0, '#fbf3df'); g0.addColorStop(1, '#d9c397'); c.fillStyle = g0; c.fillRect(0, 0, W, Hh);
      const g1 = c.createRadialGradient(x0 + D * .5, y0 + D * .9, 1, x0 + D * .5, y0 + D * .9, D * .55); g1.addColorStop(0, rgbaH(C.haut, .45)); g1.addColorStop(1, rgbaH(C.haut, 0)); c.fillStyle = g1; c.fillRect(0, 0, W, Hh);
      c.imageSmoothingQuality = 'high'; c.drawImage(pl, r[0] * s, r[1] * s, r[2] * s, r[3] * s, x0, y0, D, D);
      const u = 7.07 * D / r[2];   // px du canevas par « px studio » dans le rendu portrait (caméra 2,02 × plus serrée que l'iso)
      surTete(c, look, x0 + D * (128 - r[0]) / r[2], y0 + D * (50 - r[1]) / r[2], u * .62, C);
      c.strokeStyle = 'rgba(92,70,40,.42)'; c.lineWidth = Math.max(1, D * .025); c.beginPath(); c.arc(W / 2, Hh / 2, D / 2 - c.lineWidth / 2, 0, 7); c.stroke();
      c.restore(); return true;
    },
    // buste/plein pied pour les aperçus (éditeur de personnage, fiches) : true si dessiné
    portrait(canvas, look) {
      if (!ATLAS) return false; const T = (ATLAS.anims.repos.tailles || [128]).includes(256) ? 256 : 128, pl = ligne(look, 'repos', 1, T); if (!pl) return false;
      const c = canvas.getContext('2d'), s = T / 256; c.clearRect(0, 0, canvas.width, canvas.height);
      const cw = canvas.width, ch = canvas.height, cote = Math.min(cw, ch);
      c.imageSmoothingQuality = 'high';
      c.drawImage(pl, 40 * s, 36 * s, 176 * s, 194 * s, (cw - cote * .907) / 2, ch - cote, cote * .907, cote);
      const a = ATLAS.anims.repos, tt = a.ancres_256 && a.ancres_256.tete && a.ancres_256.tete[1] && a.ancres_256.tete[1][0];
      if (tt) { const k = cote / 194; surTete(c, look, (cw - cote * .907) / 2 + (tt[0] - 40) * k, ch - cote + (tt[1] - 36) * k, k * 3.5 * .62 / 1, couleurs(look)); }
      return true;
    }
  };
})();
