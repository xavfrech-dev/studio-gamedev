"""Essai du paquet 3 (bibliothèque standard + Node, sans navigateur) : bulles et décor.

Usage : python -I -B essai_paquet3.py      code 0 = tout vert

Chaque ligne dit comment elle vérifie : [exécuté] = le code de la page ou de paliers.js tourne sous Node ;
[lu] = contrôle par lecture du code (présence) ; [lu, vu en navigateur] = lu ici, vérifié en vrai dans le navigateur.
- bulles [exécuté] : écriture au fur et à mesure (~34 caractères/s, 6 s au plus ; au rythme de la lecture pour une phrase
  plus haute que sa zone) et RIEN d'écrit tant que la phrase n'est pas comptée ; ACCORD écriture / défilement image par
  image (la ligne en cours d'écriture toujours visible, bulle PC, bandeau téléphone, bandeau en file chargée) ; coupe en
  lignes sans perte ; hauteur limitée (6 lignes au téléphone, 10 au PC) ; page par page sans animations ; au téléphone,
  2 phrases au plus EN TOUT ; ordre du bandeau, limite d'attente, file des répliques d'un même perso ; modèle simplifié
  d'une scène chargée (12 répliques ensemble, 1 seule place de bulle : toutes vues écrites en entier) ; petit son de fin sur un faux WebAudio.
- décor [exécuté] : chaque objet mural de paliers.js est DESSINÉ sur un faux canevas à chacun de ses paliers, et tout ce
  qu'il dessine reste dans ses boîtes MURS (halo des appliques compris) ; les boîtes ne se chevauchent pas (mursEssai) ;
  la bibliothèque basse (lampe comprise) ne touche aucune boîte du mur de gauche ; une tasse dessinée sur le faux
  canevas a sa soucoupe, son anse et sa vapeur ; paliers.js en fins de ligne LF.
Limites : les boîtes des éléments fixes (fenêtres, porte, tableaux, enseigne) sont déclarées, pas mesurées sur le dessin ;
la scène chargée est un modèle de la boucle d'images, pas la page elle-même (vue en vrai dans le navigateur).
"""
import json
import os
import re
import subprocess
import sys
import tempfile

ICI = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(ICI)
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
ECHECS = []


def ok(cond, quoi):
    print(("  ok   " if cond else "  ÉCHEC ") + quoi)
    if not cond:
        ECHECS.append(quoi)


def lire(nom):
    with open(os.path.join(STUDIO, nom), encoding="utf-8", newline="") as f:
        return f.read().replace("\r\n", "\n")


def fonction(src, nom):
    """Texte d'une fonction (accolades équilibrées) dans le code de la page."""
    i = src.find("function " + nom + "(")
    if i < 0:
        return ""
    j = src.index(") {", i) + 2   # corps (pas l'accolade d'un paramètre par défaut « o = {} »)
    n = 0
    for k in range(j, len(src)):
        n += {"{": 1, "}": -1}.get(src[k], 0)
        if n == 0:
            return src[i:k + 1]
    return ""


def bloc(src, debut):
    """Texte d'un bloc qui commence à « debut » (accolades équilibrées)."""
    i = src.find(debut)
    if i < 0:
        return ""
    j = src.index("{", i)
    n = 0
    for k in range(j, len(src)):
        n += {"{": 1, "}": -1}.get(src[k], 0)
        if n == 0:
            return src[i:k + 1]
    return ""


def node(code):
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(code)
        p = f.name
    try:
        r = subprocess.run(["node", p], capture_output=True, text=True, encoding="utf-8", timeout=120)
        return r.returncode, r.stdout, r.stderr
    finally:
        os.unlink(p)


BULLES = """
const clamp = (v, a, b) => Math.min(b, Math.max(a, v)); let ANIM = true; const MOINS_MVT = { matches: false };
const BULLE_FONDU = %s;
%s
const largeur = (c, t) => [...String(t)].length * 8;   // police à chasse fixe : 8 px par caractère
%s
const r = {};
const long = 'Une phrase vraiment longue qui ne tiendrait jamais en quatre lignes dans une bulle de deux cents pixels, mais qui doit pourtant rester lisible jusqu au dernier mot sans points de suspension a la fin.';
const L = lignes(null, long, '', 178, 40); r.long_entier = L.join(' ') === long; r.sans_points = !L.some(l => l.includes('…'));
r.largeur_max = Math.max(...L.map(l => largeur(null, l)));
const mot = 'x'.repeat(60); const L2 = lignes(null, 'avant ' + mot + ' apres', '', 178, 40); r.mot_coupe = L2.every(l => largeur(null, l) <= 178) && L2.join('').replace(/ /g, '') === ('avant' + mot + 'apres');
const ins = 'aa\\u00a0bb\\u00a0cc'; r.insecable = lignes(null, ins, '', 178, 40).length === 1;
r.duree_courte = Math.round(ecritureDuree('x'.repeat(34))); r.duree_max = ecritureDuree('x'.repeat(5000));
// phrase qui tient : écriture en temps vu réel (vuT)
const qb = { texte: 'x'.repeat(68), ecr: ecritureDuree('x'.repeat(68)), tot: 10000, reste: 10000, vuT: 0 };
r.debut = ecriture(qb); qb.vuT = qb.ecr / 2; r.milieu = ecriture(qb); qb.vuT = qb.ecr + 1; r.fin = ecriture(qb);
r.pas_comptee = ecriture({ texte: 'x'.repeat(527), ecr: 6000 });   // bandeau : phrase pas encore comptée
ANIM = false; r.sans_anim = ecriture({ texte: 'x'.repeat(68), ecr: 2000, tot: 10000, reste: 10000 }) >= 68; ANIM = true;
r.lignes_tel = BULLE_LIGNES(true); r.lignes_pc = BULLE_LIGNES(false);

// ACCORD ÉCRITURE / DÉFILEMENT : une phrase plus haute que sa zone, image par image (100 ms), avec compterBulle comme dans la scène.
// À chaque image, la ligne où s'écrit la phrase doit être dans la zone visible ; rien ne s'écrit hors de la vue.
function accord(texte, nV, vite, exact) {
  const Ls = lignes(null, texte, '', 178, 40), nL = Ls.length, q = { texte, ecr: ecritureDuree(texte), cree: 0, fin: 0 };
  q.fin = q.ecr + Math.max(6, 2.6 + texte.length / 14) * 1000 + BULLE_FONDU; q._deb = nL > nV;
  const o = { nL, hors: 0, recul: 0, n_fin_t: null, tot: 0, ecrit_avant_fondu: false, haut_fin: 0, pas_max: 0, vu_ecriture: [] };
  let t = 0, hPrec = 0, nPrec = 0; compterBulle(q, false, 0, 0, vite);
  while (q.reste > 0 && t < 200000) {
    t += 100; compterBulle(q, true, 100, t, vite);
    const n = Math.min(texte.length, ecriture(q)); let m = n, cur = 0;
    for (let i = 0; i < nL; i++) { if (m <= Ls[i].length) { cur = i + m / Math.max(1, Ls[i].length); break; } m -= Ls[i].length + 1; cur = i + 1; }
    const h = defilement(q, nL, nV, exact ? cur : undefined), ligne = Math.min(nL - 1, Math.floor(cur));
    if (n > 0 && n < texte.length && (ligne < Math.floor(h) || ligne > h + nV - 1)) o.hors++;
    if (h < hPrec - 1e-9) o.recul++; if (n < nPrec) o.recul++;
    o.pas_max = Math.max(o.pas_max, h - hPrec); hPrec = h; nPrec = n;
    if (n >= texte.length && o.n_fin_t == null) o.n_fin_t = t;
    if (q.reste <= BULLE_FONDU && !o.ecrit_avant_fondu) o.ecrit_avant_fondu = n >= texte.length;
    o.haut_fin = h;
  }
  o.tot = t; o.max = Math.max(0, nL - nV); o.reste_apres_ecriture = o.n_fin_t == null ? 0 : (o.tot - o.n_fin_t) / o.tot;
  return o;
}
const p539 = ('Le relecteur a trouve trois choses a reprendre dans le chapitre deux, ' + 'une phrase tres longue qui continue encore et encore pour remplir plusieurs lignes, ').repeat(4).slice(0, 539);
r.accord_pc = accord(p539, 10, false, true);          // bulle PC : 10 lignes visibles, curseur exact
r.accord_bandeau = accord(p539.slice(0, 213), 4, false, false);   // bandeau téléphone : 4 lignes, curseur estimé au prorata
r.accord_vite = accord(p539, 6, true, false);         // bandeau PC avec une longue file : deux fois moins longtemps
// phrase qui tient, bandeau avec une longue file : l'écriture garde sa vitesse (34 caractères/s), la phrase reste moins longtemps
{ const tx = 'x'.repeat(198), q = { texte: tx, ecr: ecritureDuree(tx), cree: 0 }; q.fin = q.ecr + (2.6 + 198 / 14) * 1000 + BULLE_FONDU; compterBulle(q, false, 0, 0, true);
  let t = 0, tE = null; while (q.reste > 0) { t += 100; compterBulle(q, true, 100, t, true); if (tE == null && ecriture(q) >= 198) tE = t; }
  r.vite_tient = { ecrit_ms: tE, affiche_ms: t, tot: q.tot }; }
r.def_court = defilement({ texte: 'x', ecr: 100, tot: 1000, reste: 1000 }, 5, 6);
// sans animations : page par page sur le temps d'affichage
{ const qd = { texte: 'x'.repeat(420), ecr: 6000, tot: 39000, reste: 39000 }; ANIM = false; r.def_pages = [];
  for (let t = 0; t <= 39000; t += 1000) { qd.reste = 39000 - t; r.def_pages.push(defilement(qd, 17, 6)); } ANIM = true; }
r.maxb = [maxBulles(true, 390, false), maxBulles(true, 390, true), maxBulles(false, 800, false), maxBulles(false, 1280, false)];
const T0 = 100000, ph = (o) => Object.assign({ texte: 'x'.repeat(188), ecr: ecritureDuree('x'.repeat(188)), tot: 20000, reste: 20000, vuT: 0, cree: T0 }, o);
r.vb = {
  tel_2_bulles: versBandeau(ph({}), { tel: true, courant: false, maintenant: T0, nBulles: 2 }),
  tel_1_bulle: versBandeau(ph({}), { tel: true, courant: false, maintenant: T0, nBulles: 1 }),
  courant: versBandeau(ph({}), { tel: true, courant: true, maintenant: T0, nBulles: 2 }),
  pc_attend_3s: versBandeau(ph({}), { tel: false, courant: false, maintenant: T0 + 3000, nBulles: 0 }),
  pc_attend_1s: versBandeau(ph({}), { tel: false, courant: false, maintenant: T0 + 1000, nBulles: 0 }),
  pc_perdue_en_ecriture_2s: versBandeau(ph({ vuT: 3000, perdue: T0 + 10000 }), { tel: false, courant: false, maintenant: T0 + 12000, nBulles: 0 }),
  pc_perdue_en_ecriture_3s: versBandeau(ph({ vuT: 3000, perdue: T0 + 10000 }), { tel: false, courant: false, maintenant: T0 + 13000, nBulles: 0 }),
  pc_perdue_ecrite_1s: versBandeau(ph({ vuT: 7000, perdue: T0 + 10000 }), { tel: false, courant: false, maintenant: T0 + 11000, nBulles: 0 }),
  pc_perdue_ecrite_2s: versBandeau(ph({ vuT: 7000, perdue: T0 + 10000 }), { tel: false, courant: false, maintenant: T0 + 12000, nBulles: 0 })
};
// ordre du bandeau : en cours, puis commencées, puis les plus anciennes
{ const a = { cree: 1 }, b = { cree: 2, vue: true }, c = { cree: 3 }, d = { cree: 0 }; r.ordre = [a, b, c, d].sort((x, y) => avantBandeau(x, y, c)).map(x => x.cree); }
// limite d'attente : jamais vue → 90 s au plus ; commencée → pas de limite (elle finit à l'écran)
{ const q = { texte: 'x'.repeat(100), ecr: 3000, fin: 30000 }; compterBulle(q, false, 0, 0, false); compterBulle(q, false, 120000, 120000, false); r.limite_jamais_vue = q.fin <= 120000;
  const q3 = { texte: 'x', ecr: 30, fin: 30000 }; compterBulle(q3, false, 0, 0, false); compterBulle(q3, false, 120000, 120000, false, true); r.file_avance = q3.fin > 120000;
  compterBulle(q3, false, 200000, 320000, false, true); r.plafond_4min = q3.fin <= 320000;
  const q2 = { texte: 'x'.repeat(100), ecr: 3000, fin: 30000 }; compterBulle(q2, false, 0, 0, false); compterBulle(q2, true, 1000, 1000, false); compterBulle(q2, false, 119000, 120000, false); r.commencee_sans_limite = q2.fin > 120000; }
// nouvelle réplique d'un perso qui parle encore : elle attend son tour (2 au plus), jamais une phrase en cours effacée
{ const p = {}; let n = 1000; direBulle(p, 'premiere phrase qui s ecrit', 6, n); const b1 = p.bulle; compterBulle(b1, false, 0, n, false);
  r.file = { remplace_en_cours: !direBulle(p, 'deuxieme', 6, n + 100) && p.bulle === b1 };
  direBulle(p, 'troisieme', 6, n + 200); direBulle(p, 'quatrieme', 6, n + 300); r.file.garde_2 = p.suite.map(s => s.texte).join(',');
  compterBulle(b1, true, 30000, n + 30000, false); b1.fin = n + 30000;   // la 1re a été vue en entier et se termine
  r.file.suivante = (bulleSuivante(p, n + 30001) || {}).texte; r.file.reste = p.suite.length;
  const b2 = p.bulle; compterBulle(b2, false, 0, n + 30001, false); compterBulle(b2, true, 20000, n + 50001, false);   // écrite en entier
  r.file.remplace_ecrite = direBulle(p, 'urgent', 6, n + 50002) && p.bulle.texte === 'urgent'; }

// SCÈNE CHARGÉE (modèle simplifié de la boucle d'images : 1 seule place de bulle, comme à 1280 x 800, et 1 bandeau) : 12 répliques ensemble.
// Chacune doit être vue ENTIÈREMENT écrite avant de disparaître (aucune perdue, aucune coupée à moitié).
{ const textes = [298, 349, 213, 198, 260, 330, 150, 240, 120, 310, 280, 190].map((k, i) => 'phrase ' + i + ' ' + 'mot '.repeat(Math.ceil(k / 4)).slice(0, k - 9));
  const Q = textes.map((tx, i) => { const p = {}; direBulle(p, tx, 6, 0); p.bulle.cree = i; p.bulle._deb = lignes(null, tx, '', 178, 40).length > 10; return p.bulle; });
  const places = [], vus = new Set(), finies = new Set(); let bandeau = null, t = 0;
  Q.forEach((q, i) => { if (i %% 2) { q.reste = Math.max(0, q.fin); q.tot = q.reste; q.limite = 90000; } else compterBulle(q, false, 0, 0, false); });   // comme la page : la moitié comptée à la première image (sans compterBulle)
  while (t < 300000 && Q.some(q => q.fin > t)) {
    t += 100; const vivantes = Q.filter(q => q.fin > t);
    for (let i = places.length - 1; i >= 0; i--) if (!(places[i].fin > t)) places.splice(i, 1);
    if (bandeau && !(bandeau.fin > t)) bandeau = null;
    for (const q of vivantes) if (places.length < 1 && !places.includes(q) && q !== bandeau) places.push(q);
    const enAttente = vivantes.filter(q => !places.includes(q) && q !== bandeau);
    if (!bandeau) bandeau = enAttente.filter(q => versBandeau(q, { tel: false, courant: false, maintenant: t, nBulles: 1 })).sort((a, b) => avantBandeau(a, b, null))[0] || null;
    if (bandeau) bandeau._deb = lignes(null, bandeau.texte, '', 400, 40).length > 6;
    const attente = vivantes.filter(q => !places.includes(q) && q !== bandeau).length;
    for (const q of vivantes) { const vue = places.includes(q) || q === bandeau; compterBulle(q, vue, 100, t, q === bandeau && attente > 2, !!bandeau && q !== bandeau);
      if (vue) vus.add(q); if (ecriture(q) >= q.texte.length) finies.add(q); }
  }
  r.scene = { duree_s: t / 1000, vues: vus.size, finies: finies.size, total: Q.length }; }
console.log(JSON.stringify(r));
"""


SON = """
let joues = 0;
const noeud = () => { const p = { setValueAtTime() {}, linearRampToValueAtTime() {}, exponentialRampToValueAtTime() {}, value: 0 }, n = { connect: () => n, start: () => { joues++; }, stop() {}, frequency: p, Q: p, gain: p }; return n; };
class FauxAudio { constructor() { this.currentTime = 1; this.sampleRate = 8000; this.destination = {}; } createBuffer(c, len) { const d = new Float32Array(len); return { getChannelData: () => d }; }
  createBufferSource() { return noeud(); } createBiquadFilter() { return noeud(); } createGain() { return noeud(); } createOscillator() { return noeud(); } }
let coupe = false, ctx = null, horloge = 1000, absent = false; const vol = () => 1, LS = { v: {}, get(k, d) { return k in this.v ? this.v[k] : d; } };
const document = { hidden: false }, modeAbsent = () => absent, performance = { now: () => horloge }, window = { AudioContext: FauxAudio };
const S = { %s };
const essai = prep => { joues = 0; prep(); horloge += 1000; S.efface(); return joues; }, r = {};
r.normal = essai(() => {});
r.coupe = essai(() => { coupe = true; }); coupe = false;
r.babil = essai(() => { LS.v.babil_son = false; }); LS.v = {};
r.cache = essai(() => { document.hidden = true; }); document.hidden = false;
r.absent = essai(() => { absent = true; }); absent = false;
joues = 0; horloge += 1000; S.efface(); horloge += 100; S.efface(); r.rafale = joues;
console.log(JSON.stringify(r));
"""


def bulles(page):
    print("bulles")
    noms = ("couperMot", "lignes", "couper", "ecritureDuree", "ecritureUtile", "ecriture", "defilement", "compterBulle", "direBulle",
            "bulleSuivante", "maxBulles", "versBandeau", "avantBandeau")
    morceaux = [fonction(page, n) for n in noms]
    ok(all(morceaux), "[lu] fonctions " + ", ".join(noms) + " présentes")
    m = re.search(r"const BULLE_FONDU = (\d+);", page)
    ml = re.search(r"const BULLE_LIGNES = [^\n]*;", page)
    ok(bool(m) and 400 <= int(m.group(1)) <= 1200, "[lu] fondu de fin des bulles (BULLE_FONDU) entre 0,4 et 1,2 s")
    rc, out, err = node(BULLES % (m.group(1) if m else "700", ml.group(0) if ml else "const BULLE_LIGNES = t => 40;", "\n".join(morceaux)))
    ok(rc == 0, "[exécuté] fonctions des bulles exécutées sous Node" + (" : " + err.strip()[:300] if rc else ""))
    if rc == 0:
        r = json.loads(out.strip().splitlines()[-1])
        ok(r["long_entier"] and r["sans_points"], "[exécuté] phrase longue gardée EN ENTIER, sans « … » (jusqu'à 40 lignes)")
        ok(r["largeur_max"] <= 178, f"[exécuté] aucune ligne plus large que la bulle ({r['largeur_max']} px)")
        ok(r["mot_coupe"], "[exécuté] mot plus large que la bulle coupé, sans rien perdre")
        ok(r["insecable"], "[exécuté] l'espace insécable ne coupe pas")
        ok(r["duree_courte"] == 1000 and r["duree_max"] == 6000, f"[exécuté] écriture d'une phrase qui tient : 34 caractères/s, 6 s au plus ({r['duree_courte']} ms, {r['duree_max']} ms)")
        ok(r["debut"] == 0 and 30 <= r["milieu"] <= 38 and r["fin"] == 68, f"[exécuté] écriture progressive : 0, puis la moitié, puis la phrase entière ({r['debut']}, {r['milieu']}, {r['fin']})")
        ok(r["pas_comptee"] == 0, f"[exécuté] phrase pas encore comptée : rien d'écrit, jamais la phrase entière d'abord ({r['pas_comptee']} caractères)")
        ok(r["sans_anim"], "[exécuté] sans animations : la phrase entière tout de suite")
        ok(r["lignes_tel"] == 6 and r["lignes_pc"] == 10, f"[exécuté] hauteur limitée : {r['lignes_tel']} lignes au téléphone, {r['lignes_pc']} au PC")
        for k, quoi in (("accord_pc", "bulle PC, 10 lignes visibles"), ("accord_bandeau", "bandeau téléphone, 4 lignes, curseur estimé"), ("accord_vite", "bandeau PC, longue file (2 fois moins longtemps)")):
            a = r[k]
            ok(a["nL"] > (10 if k == "accord_pc" else 4) and a["hors"] == 0 and a["recul"] == 0,
               f"[exécuté] {quoi} : {a['nL']} lignes ; la ligne en cours d'écriture est TOUJOURS dans la zone visible (hors vue : {a['hors']} images), sans retour en arrière")
            ok(a["ecrit_avant_fondu"] and abs(a["haut_fin"] - a["max"]) < 1e-6 and a["reste_apres_ecriture"] >= .2,
               f"[exécuté] {quoi} : écrite en entier avant le fondu, défilée jusqu'à la fin, dernière page lue {a['reste_apres_ecriture'] * 100:.0f} % du temps")
            ok(a["pas_max"] < .3, f"[exécuté] {quoi} : défilement doux (au plus {a['pas_max']:.2f} ligne par image de 100 ms)")
        v = r["vite_tient"]
        ok(v["ecrit_ms"] is not None and abs(v["ecrit_ms"] - 198 / 34 * 1000) <= 200 and v["affiche_ms"] <= v["tot"] / 2 + 200 and v["affiche_ms"] - v["ecrit_ms"] >= 3000,
           f"[exécuté] bandeau avec une longue file : phrase qui tient écrite à vitesse normale ({v['ecrit_ms']} ms), affichée 2 fois moins longtemps ({v['affiche_ms']} ms sur {v['tot']:.0f}), puis lisible en entier")
        ok(r["def_court"] == 0, "[exécuté] phrase courte : pas de défilement")
        ok(set(r["def_pages"]) <= {0, 6, 11} and r["def_pages"][-1] == 11, f"[exécuté] sans animations : défilement page par page ({sorted(set(r['def_pages']))})")
        ok(r["maxb"] == [2, 1, 4, 99], f"[exécuté] téléphone : 2 bulles, 1 seule quand le bandeau parle déjà ({r['maxb']})")
        vb = r["vb"]
        ok(not vb["tel_2_bulles"] and vb["tel_1_bulle"] and vb["courant"], "[exécuté] téléphone : pas de 3e phrase dans le bandeau quand 2 bulles parlent")
        ok(vb["pc_attend_3s"] and not vb["pc_attend_1s"], "[exécuté] PC : une phrase sans place passe au bandeau après 2,5 s")
        ok(not vb["pc_perdue_en_ecriture_2s"] and vb["pc_perdue_en_ecriture_3s"] and not vb["pc_perdue_ecrite_1s"] and vb["pc_perdue_ecrite_2s"],
           "[exécuté] PC : une bulle qui perd sa place passe au bandeau (1,2 s si écrite, 2,5 s si elle s'écrivait encore)")
        ok(r["ordre"] == [3, 2, 0, 1], f"[exécuté] ordre du bandeau : la phrase en cours, puis les phrases commencées, puis les plus anciennes ({r['ordre']})")
        ok(r["limite_jamais_vue"] and r["file_avance"] and r["plafond_4min"] and r["commencee_sans_limite"],
           "[exécuté] une phrase jamais vue attend 90 s au plus hors du temps où la file avance (4 min en tout au plus) ; une phrase commencée n'a plus de limite")
        f = r["file"]
        ok(f["remplace_en_cours"] and f["garde_2"] == "troisieme,quatrieme" and f["suivante"] == "troisieme" and f["reste"] == 1 and f["remplace_ecrite"],
           f"[exécuté] nouvelle réplique d'un perso qui parle : elle attend son tour (2 au plus), jamais une phrase en cours effacée ({f})")
        s = r["scene"]
        ok(s["vues"] == s["finies"] == s["total"],
           f"[exécuté, modèle simplifié de la scène] 12 répliques lancées ensemble au PC (1 seule place de bulle, 1 bandeau) : {s['finies']}/{s['total']} vues écrites en entier, en {s['duree_s']:.0f} s")
    i_init, i_sel = page.find("qb.reste = Math.max(0, qb.fin - tI)"), page.find("versBandeau(b.o.bulle,")
    ok(0 < i_init < i_sel, "[lu] bandeau : la phrase est comptée avant d'être choisie et écrite")
    ok("sort((a, b) => avantBandeau(a.o.bulle, b.o.bulle, prB._qb))" in page and "compterBulle(qb, vue, d, tN, sans === b && attente > 2, !!sans && sans !== b)" in page
       and "vive = q => q ? bulleSuivante(q, Date.now()) : null" in page and "direBulle(p, texte, sec, Date.now())" in page,
       "[lu] la scène utilise avantBandeau, compterBulle, direBulle et bulleSuivante (essayées ci-dessus)")
    ok("qb._deb = qb._l.length > nv" in page and "qs._deb = nLB > nVB" in page and "defilement(qb, l.length, nv, cur)" in page,
       "[lu] bulle et bandeau : zone dépassée notée (_deb), défilement sur la ligne en cours d'écriture")
    ok('<span class="reste">' in page and "#parole .reste{visibility:hidden}" in page and "#parole .txt{display:block;max-height:calc(1.3em * 4)" in page,
       "[lu, vu en navigateur] bandeau : place réservée pour la phrase entière, 4 lignes au plus au téléphone, 6 au PC")
    ok("body.parole-haute #parole" in page and "classList.toggle('parole-haute', haute)" in page,
       "[lu, vu en navigateur] bandeau trop étroit à côté du micro : il passe au-dessus et s'élargit")
    ok("autres = remplace ? plats.filter(r => r !== b.r) : plats;" in page and "chevauche(r, reserves, 2)" in page,
       "[lu, vu en navigateur] bulle de décision « ? » jamais sous le texte d'une bulle (au coin d'une étiquette, ou sur une tête au téléphone)")
    # Son.efface joué sur un faux WebAudio
    i = page.find("    efface() {")
    eff = bloc(page, "    efface() {").strip() if i >= 0 else ""
    ok(bool(eff), "[lu] Son.efface présent")
    if eff:
        rc, out, err = node(SON % eff)
        ok(rc == 0, "[exécuté] Son.efface sur un faux WebAudio" + (" : " + err.strip()[:300] if rc else ""))
        if rc == 0:
            s = json.loads(out.strip().splitlines()[-1])
            ok(s["normal"] > 0, f"[exécuté] Son.efface : il sonne normalement ({s['normal']} sources)")
            ok(s["coupe"] == s["babil"] == s["cache"] == s["absent"] == 0,
               f"[exécuté] Son.efface : silencieux si son coupé, « babillage » éteint, onglet caché ou mode absent ({s})")
            ok(s["rafale"] == s["normal"], "[exécuté] Son.efface : 4 fois par seconde au plus")
    ok(page.count("Son.efface()") >= 2, "[lu] petit son au fondu, pour la bulle comme pour le bandeau")


MOCK = r"""
global.window = {}; require(%s);
const P = window.Paliers, TW = 64, TH = TW / 2, OX = 600, OY = 300;
const iso = (gx, gy, z = 0) => [OX + (gx - gy) * TW / 2, OY + (gx + gy) * TH / 2 - z * TH];
const G = { W: 16, H: 12, iso, TW: () => TW, L: () => ({ w: 1200, h: 800 }), DPR: () => 1, nuit: () => false, langue: () => 'fr', son() {}, erreur(n, e) { throw e; }, origine: () => '0', cx: () => null, surCanape: () => null, dessinePerso() {} };
const pal = P.creer(G), th = { accent: '#c9953e', accent2: '#4d6f9c', bois: '#7a5234', lumiere: '#ffd9a0', mur: '#e9dcbc', sol: '#cccccc', sol2: '#bbbbbb', cle: 'x' };
const mul = (m, n) => [m[0] * n[0] + m[2] * n[1], m[1] * n[0] + m[3] * n[1], m[0] * n[2] + m[2] * n[3], m[1] * n[2] + m[3] * n[3], m[0] * n[4] + m[2] * n[5] + m[4], m[1] * n[4] + m[3] * n[5] + m[5]];
function Ctx() { this.m = [1, 0, 0, 1, 0, 0]; this.pile = []; this.chemin = []; this.clipP = null; this.points = []; }
const C = Ctx.prototype, grad = () => ({ addColorStop() {} });
C.tr = function (x, y) { const m = this.m; return [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]]; };
C.save = function () { this.pile.push([this.m.slice(), this.clipP]); }; C.restore = function () { const s = this.pile.pop(); if (s) [this.m, this.clipP] = s; };
C.transform = function (a, b, c, d, e, f) { this.m = mul(this.m, [a, b, c, d, e, f]); }; C.setTransform = function (a, b, c, d, e, f) { this.m = [a, b, c, d, e, f]; };
C.translate = function (x, y) { this.transform(1, 0, 0, 1, x, y); }; C.scale = function (x, y) { this.transform(x, 0, 0, y, 0, 0); };
C.rotate = function (a) { this.transform(Math.cos(a), Math.sin(a), -Math.sin(a), Math.cos(a), 0, 0); };
C.beginPath = function () { this.chemin = []; this.der = null; }; C.closePath = function () {};
C.moveTo = function (x, y) { this.chemin.push(this.tr(x, y)); this.der = [x, y]; }; C.lineTo = C.moveTo;
C.quadraticCurveTo = function (cx, cy, x, y) { const [x0, y0] = this.der || [x, y]; for (let i = 1; i <= 8; i++) { const t = i / 8, u = 1 - t; this.chemin.push(this.tr(u * u * x0 + 2 * u * t * cx + t * t * x, u * u * y0 + 2 * u * t * cy + t * t * y)); } this.der = [x, y]; };
C.bezierCurveTo = function (a, b, c, d, x, y) { this.quadraticCurveTo((a + c) / 2, (b + d) / 2, x, y); };
C.ellipse = function (cx, cy, rx, ry, rot, a0, a1) { const span = Math.min(Math.abs(a1 - a0), 2 * Math.PI), sg = Math.sign(a1 - a0) || 1; for (let i = 0; i <= 32; i++) { const a = a0 + sg * span * i / 32, x = rx * Math.cos(a), y = ry * Math.sin(a); this.chemin.push(this.tr(cx + x * Math.cos(rot) - y * Math.sin(rot), cy + x * Math.sin(rot) + y * Math.cos(rot))); } };
C.arc = function (cx, cy, r, a0, a1) { this.ellipse(cx, cy, r, r, 0, a0, a1); };
C.rect = function (x, y, w, h) { for (let i = 0; i <= 4; i++) { this.chemin.push(this.tr(x + w * i / 4, y), this.tr(x + w * i / 4, y + h), this.tr(x, y + h * i / 4), this.tr(x + w, y + h * i / 4)); } };
const dans = (p, Q) => { let inn = false; for (let i = 0, j = Q.length - 1; i < Q.length; j = i++) { const [xi, yi] = Q[i], [xj, yj] = Q[j]; if ((yi > p[1]) !== (yj > p[1]) && p[0] < (xj - xi) * (p[1] - yi) / (yj - yi) + xi) inn = !inn; } return inn; };
const enveloppe = pts => { const s = pts.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]), cr = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]), lo = [], hi = [];
  for (const p of s) { while (lo.length >= 2 && cr(lo[lo.length - 2], lo[lo.length - 1], p) <= 0) lo.pop(); lo.push(p); }
  for (const p of s.reverse()) { while (hi.length >= 2 && cr(hi[hi.length - 2], hi[hi.length - 1], p) <= 0) hi.pop(); hi.push(p); } return lo.slice(0, -1).concat(hi.slice(0, -1)); };
C.clip = function () { this.clipP = enveloppe(this.chemin); };   // ce qui est dessiné ensuite reste dans la zone découpée
C.trace = function (pts) { if (this.clipP) this.points.push(...pts.filter(p => dans(p, this.clipP)), ...this.clipP); else this.points.push(...pts); };
C.fill = function () { this.trace(this.chemin); }; C.stroke = C.fill;
C.fillRect = function (x, y, w, h) { this.beginPath(); this.rect(x, y, w, h); this.fill(); }; C.strokeRect = C.fillRect;
C.fillText = function () {}; C.measureText = () => ({ width: 10 }); C.setLineDash = function () {}; C.drawImage = function () {};
C.createLinearGradient = grad; C.createRadialGradient = grad;
const versMur = (mur, [X, Y]) => { const u = mur === 'g' ? (OX - X) / (TW / 2) : (X - OX) / (TW / 2); return [u, (OY + u * TH / 2 - Y) / TH]; };
const out = [];
for (const it of pal.muraux()) for (let p = it.de; p <= (it.a || 5); p++) {
  const B = P.MURS.filter(m => (m.o || m.id) === it.id && p >= m.de && p <= m.a);
  if (!B.length) { out.push({ id: it.id, p, erreur: 'aucune boîte MURS' }); continue; }
  const c = new Ctx(); try { it.f(c, th, p, 12.3); } catch (e) { out.push({ id: it.id, p, erreur: String(e.message) }); continue; }
  let pire = 0; const mur = B[0].mur;
  for (const pt of c.points) { const [u, z] = versMur(mur, pt), d = Math.min(...B.map(b => Math.max(b.u0 - u, u - b.u1, b.z0 - z, z - b.z1, 0))); pire = Math.max(pire, d); }
  out.push({ id: it.id, p, points: c.points.length, depasse: +pire.toFixed(3), murs: new Set(B.map(b => b.mur)).size });
}
// tasse seule, dessinée sur le faux canevas : soucoupe (ellipse pleine), anse (demi-ellipse tracée à droite du corps), vapeur (volutes blanches)
const T = new Ctx(); T.el = [];
T.ellipse = function (cx, cy, rx, ry, rot, a0, a1) { this.el.push({ cx, cy, rx, ry, a0, a1 }); C.ellipse.call(this, cx, cy, rx, ry, rot, a0, a1); };
T.fill = function () { const l = this.el[this.el.length - 1]; if (l && !l.op) { l.op = 'fill'; l.st = String(this.fillStyle); } C.fill.call(this); };
T.stroke = function () { const l = this.el[this.el.length - 1]; if (l && !l.op) l.op = 'stroke'; C.stroke.call(this); };
pal.tasseEssai(T, { vapeur: true });
const tasse = { soucoupe: T.el.some(e => e.op === 'fill' && e.rx >= 4 && e.ry >= 1.8 && e.ry < e.rx && !/^rgba/.test(e.st)),
  anse: T.el.some(e => e.op === 'stroke' && Math.abs(e.a0 + Math.PI / 2) < 1e-6 && Math.abs(e.a1 - Math.PI / 2) < 1e-6 && e.cx > 2),
  vapeur: T.el.filter(e => e.op === 'fill' && /^rgba\(255,255,255,/.test(e.st)).length };
console.log(JSON.stringify({ murs: out, tasse }));
"""


def decor(page, pal, brut_pal):
    print("décor")
    ok(b"\r" not in brut_pal, "paliers.js en fins de ligne LF (comme la base)")
    m = re.search(r"// MURS-DEBUT \(JSON strict\)\s*const MURS = (\[.*?\]);\s*// MURS-FIN", pal, re.S)
    ok(bool(m), "registre MURS lisible (JSON strict)")
    if not m:
        return
    murs = json.loads(m.group(1))
    rc, out, err = node("global.window = {}; require(%s); console.log(JSON.stringify(window.Paliers.mursEssai()));" % json.dumps(os.path.join(STUDIO, "paliers.js")))
    vert = rc == 0 and all(not v["chevauchements"] and not v["hors_mur"] for v in json.loads(out).values())
    ok(vert, "Paliers.mursEssai() : aucune boîte murale n'en chevauche une autre, rien hors du mur, à chaque palier" + ("" if vert else " : " + (err or out).strip()[:400]))
    rc, out, err = node(MOCK % json.dumps(os.path.join(STUDIO, "paliers.js")))
    ok(rc == 0, "objets muraux dessinés sur un faux canevas" + (" : " + err.strip()[:300] if rc else ""))
    if rc == 0:
        D = json.loads(out.strip().splitlines()[-1])
        res = D["murs"]
        mauvais = [x for x in res if x.get("erreur") or x["depasse"] > .06 or not x["points"] or x["murs"] != 1]
        ids = sorted({x["id"] for x in res})
        ok(not mauvais, f"{len(ids)} objets muraux dessinés à chacun de leurs paliers : rien hors de leurs boîtes MURS (écart toléré 0,06)"
           + (f" ; hors boîte : {mauvais}" if mauvais else f" (pire écart {max(x['depasse'] for x in res):.3f})"))
        ok({"appliques", "panneaux_acoustiques", "affiches", "ecrans_muraux", "neon", "trophees", "radiateur", "guirlande", "horloge",
            "cadre_paysage", "barometre", "etagere_murale", "plante_suspendue"} <= set(ids),
           "contrôlés : appliques (halo compris), panneaux, affiches, écrans, néon, trophées, radiateur, guirlande, horloge, cadre, baromètre, étagère, plante")
    # bibliothèque basse : caisson + lampe (sommet à BIBLIO_H + .28), contre le mur de gauche ; ne touche aucune boîte de ce mur
    mh = re.search(r"const BIBLIO_H = ([\d.]+), BIBLIO_U = p => p >= 5 \? \[([\d.]+), ([\d.]+)\] : \[([\d.]+), ([\d.]+)\];", page)
    ok(bool(mh) and "lampe : sommet à h + .28" in page, "bibliothèque basse : hauteur et place lues dans la page")
    if mh:
        h = float(mh.group(1)) + .28
        u5, u14 = (float(mh.group(2)), float(mh.group(3))), (float(mh.group(4)), float(mh.group(5)))
        gene = []
        for p in range(1, 6):
            u0, u1 = u5 if p >= 5 else u14
            for b in murs:
                if b["mur"] == "g" and b["de"] <= p <= b["a"] and min(u1, b["u1"]) - max(u0, b["u0"]) > 0 and h > b["z0"]:
                    gene.append(f"palier {p} : {b['id']}")
        ok(not gene, f"bibliothèque (lampe comprise, sommet à {h:.2f}) : ni devant la fenêtre ou la verrière, ni sur un objet mural" + (f" ({gene})" if gene else ""))
        emp = re.findall(r'\{ "id": "etagere_livres", "de": (\d), "a": (\d), "r": \[0\.15, ([\d.]+), 0\.7, ([\d.]+)\] \}', page)
        f = lambda v: f"{v:g}"
        ok(sorted(emp) == sorted([("1", "4", f(u14[0]), f(u14[1])), ("5", "5", f(u5[0]), f(u5[1]))]), f"emprise au sol de la bibliothèque à jour ({emp})")
        corps = bloc(page, "etagere_livres(th) {")
        ok("intérieur du caisson" in corps and "// rayon" in corps and "while (u < y1" in corps, "[lu, vu en navigateur] bibliothèque : intérieur sombre, rayons et livres de largeurs variées vus de face")
        ta = D["tasse"]
        ok(ta["soucoupe"] and ta["anse"] and ta["vapeur"] >= 3, f"[exécuté] tasse dessinée sur un faux canevas : soucoupe, anse, vapeur légère ({ta})")
    ok(pal.count("tasse(c, ") >= 4, "[lu, vu en navigateur] tasses posées sur les bureaux, au café et à l'îlot")


def main():
    brut_page = open(os.path.join(STUDIO, "studio.html"), "rb").read()
    ok(brut_page.count(b"\r\n") in (0, brut_page.count(b"\n")), "studio.html : fins de ligne homogènes")
    page = lire("studio.html")
    brut = open(os.path.join(STUDIO, "paliers.js"), "rb").read()
    bulles(page)
    decor(page, brut.decode("utf-8"), brut)
    print("OK : tout est vert" if not ECHECS else f"ÉCHEC : {len(ECHECS)} point(s)")
    return 0 if not ECHECS else 1


if __name__ == "__main__":
    sys.exit(main())
