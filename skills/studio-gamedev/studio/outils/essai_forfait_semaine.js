// Essai sans navigateur de la puce du forfait (node studio/outils/essai_forfait_semaine.js) : majForfait() de studio.html
// est extraite et jouée avec un petit faux DOM. Compte SANS fenêtre de 5 h (« 5 h » absente, pct null, ou seulement des fenêtres
// hebdo) : la puce dit « Semaine N % » (N = % UTILISÉ de la semaine, barre remplie d'autant) ; avant, elle montrait le % RESTANT
// sans le dire (« 90 % » pour une semaine à 10 %). Avec une fenêtre de 5 h : comportement d'avant (% restant de la plus entamée).
// Test of the plan chip: an account without a 5-hour window reads "Week N%" (used), otherwise unchanged. Exit code 1 on any gap.
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm');
const html = fs.readFileSync(path.join(__dirname, '..', 'studio.html'), 'utf8');
const i0 = html.indexOf('function majForfait() {'), fin = /\r?\n\}\r?\n/g; fin.lastIndex = Math.max(0, i0);
const mf = i0 < 0 ? null : fin.exec(html), i1 = mf ? mf.index + mf[0].length : -1;
if (i0 < 0 || i1 < 0) { console.log('ÉCART  majForfait introuvable dans studio.html'); process.exit(1); }
const src = html.slice(i0, i1);

function element(id) {
  const attrs = {}, classes = new Set();
  return { id, hidden: true, textContent: '', title: '', dataset: {}, style: { width: '' },
    classList: { toggle(c, v) { if (v === undefined ? !classes.has(c) : v) classes.add(c); else classes.delete(c); }, contains: c => classes.has(c) },
    getAttribute: k => (k in attrs ? attrs[k] : null), setAttribute(k, v) { attrs[k] = String(v); }, attrs, classes,
    querySelector: () => null };
}
function monter(langue) {
  const els = { '#forfait': element('forfait'), '#forfait-plein': element('forfait-plein'), '#forfait .piste': element('piste'),
    '#forfait-pct': element('forfait-pct'), '#forfait-rebours': element('forfait-rebours') };
  const lib = element('lib'); lib.textContent = 'Forfait Claude';
  els['#forfait'].querySelector = s => (s === 'span[data-t="forfait"]' ? lib : null);
  const ctx = { console, Date, Math, Number, String, isNaN, JSON, LANGUE: langue, CONF: { mode: 'travail' }, FORFAIT: { d: null },
    $: s => els[s] || null, clamp: (v, a, b) => Math.min(b, Math.max(a, v)), pctT: n => (langue === 'en' ? n + '%' : n + ' %'),
    seuilForfait: () => 3600000, rebours: () => '', deuxC: x => String(x).padStart(2, '0'), ajusterOutils() {}, majForfaitOptim() {} };
  vm.createContext(ctx); vm.runInContext(src, ctx);
  return { ctx, els, lib };
}
let err = 0, n = 0;
const egal = (quoi, obtenu, attendu) => { n++; if (obtenu !== attendu) { err++; console.log('ÉCART  ' + quoi + ' : ' + JSON.stringify(obtenu) + ' au lieu de ' + JSON.stringify(attendu)); } };
const iso = ms => new Date(Date.now() + ms).toISOString();
function jouer(fenetres, langue = 'fr') {
  const m = monter(langue);
  m.ctx.FORFAIT.d = { maj: new Date().toISOString(), offre: 'Max', fenetres };
  vm.runInContext('majForfait()', m.ctx);
  const f = m.els['#forfait'];
  return { semaine: f.classes.has('semaine'), pct: m.els['#forfait-pct'].textContent, mot: m.els['#forfait-pct'].dataset.mot, lib: m.lib.textContent,
    largeur: m.els['#forfait-plein'].style.width, aria: m.els['#forfait .piste'].attrs['aria-valuetext'] || '', titre: f.title, cache: f.hidden };
}

// 1. fenêtre de 5 h marquée absente (pct null) + semaine à 10 % : « Semaine 10 % », barre à 10 %
let r = jouer([{ nom: 'Session (5 h)', pct_utilise: null, absente: true }, { nom: 'Semaine · tous les modèles', pct_utilise: 10, remise_a_zero: iso(4 * 864e5) }]);
egal('sans 5 h : affichée', r.cache, false);
egal('sans 5 h : mode semaine', r.semaine, true);
egal('sans 5 h : % utilisé de la semaine', r.pct, '10 %');
egal('sans 5 h : mot devant le %', r.mot, 'Semaine');
egal('sans 5 h : étiquette', r.lib, 'Semaine utilisée');
egal('sans 5 h : barre remplie du % utilisé', r.largeur, '10%');
egal('sans 5 h : lecteur d’écran dit utilisés et restants', /10 % de la semaine utilisés, 90 % restants/.test(r.aria), true);
egal('sans 5 h : info-bulle explique', /pas de fenêtre de 5 h/.test(r.titre), true);
// 2. seulement des fenêtres hebdo, sans fenêtre de 5 h listée
r = jouer([{ nom: 'Hebdo · tous les modèles', pct_utilise: 12, remise_a_zero: iso(4 * 864e5) }, { nom: 'Hebdo · autre modèle', pct_utilise: 0, remise_a_zero: iso(4 * 864e5) }]);
egal('hebdo seules : mode semaine', r.semaine, true);
egal('hebdo seules : plus entamée = 12 % utilisés', r.pct, '12 %');
// 3. avec une fenêtre de 5 h : inchangé (% RESTANT de la plus entamée)
r = jouer([{ nom: 'Session (5 h)', pct_utilise: 70, remise_a_zero: iso(2 * 36e5) }, { nom: 'Semaine', pct_utilise: 10, remise_a_zero: iso(4 * 864e5) }]);
egal('avec 5 h : pas de mode semaine', r.semaine, false);
egal('avec 5 h : % restant', r.pct, '30 %');
egal('avec 5 h : étiquette', r.lib, 'Forfait Claude');
egal('avec 5 h : barre du reste', r.largeur, '30%');
r = jouer([{ nom: '5 heures', pct_utilise: 40, remise_a_zero: iso(2 * 36e5) }, { nom: 'Hebdo', pct_utilise: 10, remise_a_zero: iso(4 * 864e5) }]);
egal('avec « 5 heures » : % restant', r.pct, '60 %');
egal('avec « 5 heures » : pas de mode semaine', r.semaine, false);
// 4. anglais
r = jouer([{ nom: '5 h', pct_utilise: null, absente: true }, { nom: 'Week', pct_utilise: 10, remise_a_zero: iso(4 * 864e5) }], 'en');
egal('EN sans 5 h : « Week 10% »', r.mot + ' ' + r.pct, 'Week 10%');
egal('EN sans 5 h : étiquette', r.lib, 'Week used');
// 5. fenêtre non nommée (ancien format) : inchangé
r = jouer([{ nom: 'Fenêtre', pct_utilise: 25 }]);
egal('fenêtre sans nom connu : % restant', r.pct, '75 %');
egal('fenêtre sans nom connu : pas de mode semaine', r.semaine, false);

console.log(err ? `${err} écart(s) sur ${n}` : `tout vert (${n} vérifications)`);
process.exit(err ? 1 : 0);
