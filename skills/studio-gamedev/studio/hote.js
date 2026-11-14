// studio/hote.js : l'hôte du studio, un personnage d'ambiance que l'utilisateur crée lui-même (quête « Un hôte pour le studio »).
// Chargé après le script principal de studio.html (et quetes_page.js) : il réutilise ses outils ($, esc, t, Panneau, toast,
// Son, poster, lire, Bureau, LANGUE, CONF, LS, modeAbsent, decisionsOuvertes, ETAT…). Trois parties :
//  1. la création : par des choix (allure, couleurs, accessoire, coin, 3 ou 4 activités, objets, ton, nom) ou par un prompt
//     (texte filtré, envoyé à l'assistant par une demande « hote » ; il renvoie une fiche composée avec les pièces du skill,
//     .studio/hote_proposition.json, montrée en aperçu avant d'installer l'hôte) ;
//  2. la scène : son coin (fauteuil, guéridon, tapis et objets choisis), ses activités, ce qu'il tient en main, ses répliques
//     (règles du bavardage du studio : babillage coupé, mode absent, onglet caché, téléphone, jamais deux fois la même en 30 min)
//     et ses sons, très discrets ;
//  3. les Réglages : sons, fréquence des répliques, modifier, supprimer (il part par la porte ; sa fiche est gardée dans
//     .studio/anciens/). Pièces et filtre : hote_catalogue.json ; contrôle côté serveur : hote.py.
'use strict';
(() => {
  if (typeof Panneau === 'undefined' || typeof TXT === 'undefined' || typeof Bureau === 'undefined') return;

  // ------------------------------------------------------------------ textes (fr = en, mêmes clés)
  Object.assign(TXT.fr, {
    ho_titre: 'Crée l’hôte de ton studio', ho_intro: 'Un personnage qui vit dans un coin du studio : il a ses habitudes, il passe voir l’équipe et dit un mot de temps en temps. Il ne travaille pas sur le jeu : il habite le studio.',
    ho_par_choix: 'Je le compose', ho_par_choix_d: 'des choix à cliquer, étape par étape', ho_par_prompt: 'Je le décris', ho_par_prompt_d: 'une phrase, l’assistant compose la fiche',
    ho_e_allure: 'Son allure', ho_e_couleurs: 'Ses couleurs', ho_e_accessoire: 'Un accessoire', ho_e_coin: 'Son coin du studio', ho_e_activites: 'Ce qu’il fait (3 ou 4)',
    ho_e_objets: 'Ses objets (3 au plus)', ho_e_ton: 'Sa façon de parler', ho_e_nom: 'Son nom', ho_suivant: 'Suivant', ho_retour: 'Retour', ho_hasard: 'Au hasard',
    ho_installer: 'Il s’installe !', ho_nom_ph: 'Un prénom, un surnom…', ho_choisis: 'choisis-en {n}', ho_choisis_max: '{n} au plus', ho_apporte: 'apporté pour « {a} »',
    ho_prompt_t: 'Décris ton hôte', ho_prompt_aide: 'Son allure, ses couleurs, ce qu’il aime faire, sa façon de parler. L’assistant compose la fiche avec les pièces du studio (rien n’est généré ni payé) ; tu verras l’aperçu avant qu’il s’installe.',
    ho_prompt_ph: 'Ex. : une jardinière souriante en salopette verte, avec un chapeau, qui arrose ses plantes, lit près de la fenêtre et encourage tout le monde.',
    ho_envoyer: 'Envoyer à l’assistant', ho_attente: 'L’assistant compose ton hôte…', ho_attente_d: 'La fiche arrive ici dès qu’elle est prête (tu peux fermer, une notification te préviendra).',
    ho_annuler: 'Annuler', ho_apercu: 'Voici ton hôte', ho_retoucher: 'Retoucher avec les choix', ho_recommencer: 'Recommencer', ho_refusee: 'La fiche n’a pas pu être faite',
    ho_pret_toast: 'Ton hôte est prêt.', ho_arrive: '{n} s’installe {c}.', ho_parti: '{n} est parti. Sa fiche est gardée dans .studio/anciens/.',
    ho_reglages: 'Hôte du studio', ho_sons: 'Ses sons (très discrets)', ho_parole: 'Il parle', ho_p_souvent: 'souvent', ho_p_normal: 'de temps en temps', ho_p_rarement: 'rarement', ho_p_jamais: 'jamais',
    ho_modifier: 'Modifier', ho_supprimer: 'Supprimer', ho_confirmer: 'Oui, le supprimer', ho_pas_encore: 'Pas encore d’hôte : il arrive avec la quête « Un hôte pour le studio ».', ho_creer: 'Créer mon hôte',
    ho_fiche_sur: 'Hôte du studio', ho_maintenant: 'En ce moment', ho_activites: 'Ses habitudes', ho_ton: 'Ton', ho_coin: 'Coin', ho_faire_parler: 'Lui dire bonjour',
    ho_repos: 'se repose dans son fauteuil', ho_arrivee: 'arrive au studio', ho_depart: 'part du studio', ho_vers: 'va vers', ho_filtre: 'Refusé : garde-le gentil et tout public (rien de vulgaire, ni drogue ni alcool, rien de dénigrant).',
    ho_exemples: 'Exemples', ho_ex1: 'Un vieux marin calme en caban bleu, qui lit et raconte des histoires de mer.', ho_ex2: 'Une petite bricoleuse enthousiaste en salopette jaune, qui range tout et met de la musique.', ho_ex3: 'Un poète rêveur à béret qui croque le studio dans son carnet.',
    ho_avert: 'Ajusté par le studio', ho_merci: 'Merci !'
  });
  Object.assign(TXT.en, {
    ho_titre: 'Create your studio host', ho_intro: 'A character who lives in a corner of the studio: they have habits, drop by the team and say a word now and then. They do not work on the game: they live in the studio.',
    ho_par_choix: 'I build them', ho_par_choix_d: 'cards to click, step by step', ho_par_prompt: 'I describe them', ho_par_prompt_d: 'one sentence, the assistant builds the sheet',
    ho_e_allure: 'Their look', ho_e_couleurs: 'Their colours', ho_e_accessoire: 'An accessory', ho_e_coin: 'Their studio corner', ho_e_activites: 'What they do (3 or 4)',
    ho_e_objets: 'Their objects (3 at most)', ho_e_ton: 'How they talk', ho_e_nom: 'Their name', ho_suivant: 'Next', ho_retour: 'Back', ho_hasard: 'Random',
    ho_installer: 'Move in!', ho_nom_ph: 'A first name, a nickname…', ho_choisis: 'pick {n}', ho_choisis_max: '{n} at most', ho_apporte: 'brought for “{a}”',
    ho_prompt_t: 'Describe your host', ho_prompt_aide: 'Their look, colours, what they like doing, how they talk. The assistant builds the sheet from the studio pieces (nothing generated, nothing paid); you see a preview before they move in.',
    ho_prompt_ph: 'E.g.: a smiling gardener in green overalls and a hat, who waters plants, reads by the window and cheers everyone up.',
    ho_envoyer: 'Send to the assistant', ho_attente: 'The assistant is building your host…', ho_attente_d: 'The sheet shows up here as soon as it is ready (you can close this, a notification will tell you).',
    ho_annuler: 'Cancel', ho_apercu: 'Here is your host', ho_retoucher: 'Fine-tune with the cards', ho_recommencer: 'Start over', ho_refusee: 'The sheet could not be made',
    ho_pret_toast: 'Your host is ready.', ho_arrive: '{n} moves in {c}.', ho_parti: '{n} left. Their sheet is kept in .studio/anciens/.',
    ho_reglages: 'Studio host', ho_sons: 'Their sounds (very quiet)', ho_parole: 'They talk', ho_p_souvent: 'often', ho_p_normal: 'now and then', ho_p_rarement: 'rarely', ho_p_jamais: 'never',
    ho_modifier: 'Edit', ho_supprimer: 'Remove', ho_confirmer: 'Yes, remove them', ho_pas_encore: 'No host yet: they come with the quest “A host for the studio”.', ho_creer: 'Create my host',
    ho_fiche_sur: 'Studio host', ho_maintenant: 'Right now', ho_activites: 'Habits', ho_ton: 'Tone', ho_coin: 'Corner', ho_faire_parler: 'Say hello',
    ho_repos: 'rests in the armchair', ho_arrivee: 'arrives at the studio', ho_depart: 'leaves the studio', ho_vers: 'walks to', ho_filtre: 'Refused: keep it kind and family-friendly (nothing vulgar, no drugs or alcohol, nothing demeaning).',
    ho_exemples: 'Examples', ho_ex1: 'A calm old sailor in a blue pea coat, who reads and tells sea stories.', ho_ex2: 'A small cheerful handywoman in yellow overalls, who tidies everything and plays music.', ho_ex3: 'A dreamy poet in a beret who sketches the studio in a notebook.',
    ho_avert: 'Adjusted by the studio', ho_merci: 'Thanks!'
  });
  const L = o => (o && typeof o === 'object') ? (o[LANGUE] || o.fr || o.en || '') : String(o || '');
  const ICONES = { boisson: 'tasse', arrose: 'pousse', lit: 'livre', fenetre: 'soleil', tournee: 'equipe', musique: 'musique_douce', range: 'boites', carnet: 'carnet',
    tapis: 'maison', plante: 'pousse', lampe: 'bougie', livres: 'bibliotheque', radio: 'note', aquarium: 'onde',
    chaleureux: 'coeur', pince_sans_rire: 'sarcastique', poetique: 'plume', enthousiaste: 'etincelles', sage: 'serieux' };
  const icone = id => ICONES[id] ? `<img class="ho-ic" src="cartes/${ICONES[id]}.svg" alt="">` : '';

  const STYLE = document.createElement('style');
  STYLE.textContent = `
.ho-grille{display:grid;grid-template-columns:repeat(auto-fill,minmax(132px,1fr));gap:10px;margin-top:12px}
.ho-carte{border:1px solid rgba(92,79,63,.28);background:#fffdf6;border-radius:12px;padding:10px;text-align:center;color:var(--encre);cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:6px;min-height:44px;font:14px var(--sans)}
.ho-carte:hover{border-color:var(--ocre)}.ho-carte.choisie{border:2px solid var(--ocre);background:#fff4dc;box-shadow:0 0 0 3px rgba(226,184,102,.25)}
.ho-carte canvas{width:96px;height:96px}.ho-carte small{color:var(--encre3);font-size:12px;line-height:1.3}
.ho-ic{width:34px;height:34px;opacity:.85}.ho-nuancier{display:flex;gap:4px}.ho-nuancier i{width:22px;height:22px;border-radius:50%;border:1px solid rgba(0,0,0,.2);display:block}
.ho-deux{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:14px}.ho-deux .ho-carte{padding:18px 12px}.ho-deux .ho-carte b{font-size:16px}
.ho-pas{display:flex;gap:5px;margin:6px 0 2px}.ho-pas i{width:8px;height:8px;border-radius:50%;background:rgba(92,79,63,.25)}.ho-pas i.on{background:var(--ocre)}
.ho-tete{display:flex;gap:14px;align-items:center}.ho-tete canvas{width:120px;height:120px;flex:none}
.ho-zone{width:100%;min-height:96px;border-radius:10px;border:1px solid rgba(92,79,63,.3);padding:10px;font:15px var(--sans);resize:vertical;box-sizing:border-box}
.ho-erreur{color:var(--rouge);font-size:13px;min-height:18px}.ho-ex{display:block;text-align:left;margin:4px 0;font-size:13px}
.ho-liste{margin:6px 0 0 18px;padding:0}.ho-liste li{margin:2px 0}.ho-cite{font-style:italic;color:var(--encre2)}
.ho-rg{display:flex;gap:10px;align-items:center;margin:6px 0}.ho-rg canvas{width:52px;height:52px}
.ho-roue{width:28px;height:28px;border-radius:50%;border:3px solid rgba(185,133,50,.25);border-top-color:var(--ocre);animation:ho-tour 1s linear infinite;display:inline-block;vertical-align:middle;margin-right:8px}
@keyframes ho-tour{to{transform:rotate(360deg)}}@media (prefers-reduced-motion:reduce){.ho-roue{animation:none}}
.ho-supprimer.confirme{background:var(--rouge);color:#fff;border-color:var(--rouge)}
@media (max-width:520px){.ho-grille{grid-template-columns:repeat(2,1fr)}.ho-deux{grid-template-columns:1fr}.ho-tete canvas{width:92px;height:92px}}`;
  document.head.appendChild(STYLE);

  // ------------------------------------------------------------------ données
  let CAT = null, H = null, PROP = null, SIG_H = '', SIG_P = '', PREMIER = true;
  const parId = (cle, id) => CAT && (CAT[cle] || []).find(x => x.id === id);
  async function charger() {
    try {
      if (!CAT) { const c = await lire('hote_catalogue.json'); if (c && Array.isArray(c.coins)) CAT = c; else return; }
      const [h, p] = await Promise.all([lire('hote.json'), lire('hote_proposition.json')]);
      const sh = JSON.stringify(h || null), sp = JSON.stringify(p || null);
      if (sh !== SIG_H) { const avant = present(); H = (h && typeof h === 'object' && h.nom) ? h : null; SIG_H = sh; changement(avant, H); }
      if (sp !== SIG_P) { const avant = PROP; PROP = (p && typeof p === 'object') ? p : null; SIG_P = sp; if (!PREMIER) propositionChangee(avant, PROP); }
      PREMIER = false;
    } catch (e) { erreur('hôte du studio', e); }
  }
  setInterval(() => { if (!document.hidden) charger(); }, 4000);
  charger();
  window.addEventListener('studio:roadmap', () => charger());

  // ------------------------------------------------------------------ règles de contenu (même algorithme que hote.py filtrer)
  // « mot » : mot entier ; « mot* » : début de mot ; « ~mot » : n'importe où dans le mot ; « deux mots » : expression ;
  // exceptions et expressions permises toujours acceptées. Pas de regex qui regarde en arrière (Safari < 16.4 ne la lit pas).
  const SOSIES = { 'α': 'a', 'β': 'b', 'ε': 'e', 'η': 'n', 'ι': 'i', 'κ': 'k', 'ν': 'v', 'ο': 'o', 'ρ': 'p', 'τ': 't', 'υ': 'u', 'χ': 'x', 'ς': 'c', 'σ': 'o', 'μ': 'u', 'γ': 'y', 'ω': 'w', 'а': 'a', 'в': 'b', 'е': 'e', 'ё': 'e', 'к': 'k', 'м': 'm', 'н': 'h', 'о': 'o', 'р': 'p', 'с': 'c', 'т': 't', 'у': 'y', 'х': 'x', 'і': 'i', 'ї': 'i', 'ј': 'j', 'ѕ': 's', 'ԁ': 'd', 'ɡ': 'g', 'ı': 'i', 'ł': 'l', 'ø': 'o', 'đ': 'd', 'ß': 'ss', 'œ': 'oe', 'æ': 'ae' };
  const LEET = { 0: 'o', 1: 'i', 3: 'e', 4: 'a', 5: 's', 7: 't', '@': 'a', $: 's', '€': 'e', '!': 'i' };
  let RE_INV = /[\u0300-\u036f\u00ad\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]/g;
  try { RE_INV = new RegExp('[\\p{Mn}\\p{Me}\\p{Cf}]', 'gu'); } catch (e) { /* navigateur ancien : liste fixe */ }
  const sansAcc = s => String(s || '').normalize('NFKD').replace(RE_INV, '');
  const simplifier = s => sansAcc(Array.from(sansAcc(s).toLowerCase(), c => SOSIES[c] || c).join('')).replace(/[0134578@$€!]/g, c => LEET[c] || c).replace(/([a-z])[*#._-]+(?=[a-z])/g, '$1');
  const jetons = s => simplifier(s).match(/[a-z]+/g) || [];
  function recolles(brut) { const out = []; for (let i = 0; i < brut.length;) { let j = i; while (j < brut.length && brut[j].length === 1) j++; if (j - i >= 3) out.push(brut.slice(i, j).join('')); i = Math.max(j, i + 1); } return out; }
  const motif = m => jetons(m.replace(/\*$/, '')).join(' ') + (/\*\s*$/.test(m) ? '*' : '');
  const exempte = (m, ex) => ex.some(e => e.endsWith('*') ? m.startsWith(e.slice(0, -1)) : m === e);
  function filtrer(texte) {
    if (!CAT || !CAT.filtre) return [];
    const f = CAT.filtre, brut = jetons(texte), neutre = brut.map(() => false);
    for (const e of f.expressions_permises || []) { const ej = jetons(e), n = ej.length; if (!n) continue; for (let i = 0; i + n <= brut.length; i++) if (ej.every((x, k) => brut[i + k] === x)) for (let k = i; k < i + n; k++) neutre[k] = true; }
    const ex = (f.exceptions || []).map(motif), seq = brut.map((m, i) => neutre[i] || exempte(m, ex) ? '_' : m);
    const mots = seq.filter(m => m !== '_').concat(recolles(brut).filter(m => !exempte(m, ex))), tous = new Set();
    for (const m of mots) { tous.add(m); tous.add(m.replace(/(.)\1{2,}/g, '$1')); tous.add(m.replace(/(.)\1+/g, '$1')); }
    const phrase = ' ' + seq.join(' ') + ' ', out = [];
    for (const cat of ['vulgaire', 'drogue', 'denigrant']) for (const mot of f[cat] || []) {
      const brutMot = String(mot).trim(), dedans = brutMot.startsWith('~'), m = motif(brutMot.replace(/^~/, '')); if (!m || m === '*') continue;
      const r = m.replace(/\*$/, ''), ok = dedans ? [...tous].some(x => x.includes(r))
        : m.includes(' ') ? (phrase.includes(' ' + r + ' ') || (m.endsWith('*') && phrase.includes(' ' + r)))
        : m.endsWith('*') ? [...tous].some(x => x.startsWith(r)) : tous.has(m);
      if (ok) out.push([cat, mot]);
    }
    return out;
  }

  // ------------------------------------------------------------------ fiche -> look, textes
  function lookDeFiche(f) {
    if (!f) return null;
    if (f.look && typeof f.look === 'object') return f.look;
    const a = parId('allures', f.allure), c = parId('couleurs', f.couleurs), l = JSON.parse(JSON.stringify((a && a.look) || {}));
    l.tenue = Object.assign({}, l.tenue || {}, c ? { couleur1: c.couleur1, couleur2: c.couleur2 } : {}); if (f.accessoire) l.accessoire = f.accessoire; return l;
  }
  function repliques(cle) {
    if (!H || !CAT) return [];
    if (H.repliques && Array.isArray(H.repliques[cle]) && H.repliques[cle].length) return H.repliques[cle];
    const ton = parId('tons', H.ton) || CAT.tons[0], r = ton.repliques[LANGUE] || ton.repliques.fr; return r[cle] || [];
  }
  function repliquesActivite(id) {
    if (!H || !CAT) return [];
    if (H.repliques && H.repliques.activites && Array.isArray(H.repliques.activites[id]) && H.repliques.activites[id].length) return H.repliques.activites[id];
    const a = parId('activites', id); return a ? (a.repliques[LANGUE] || a.repliques.fr) : [];
  }
  const coin = () => (H && parId('coins', H.coin)) || (CAT && CAT.coins[0]);

  // ------------------------------------------------------------------ parole (règles du bavardage du studio)
  const DITS = new Map(); let DERNIER = 0;
  const permis = () => LS.get('babil', true) !== false && CONF.mode === 'travail' && !document.hidden && !(typeof modeAbsent === 'function' && modeAbsent());
  const intervalle = () => { const p = (H && H.reglages && H.reglages.parole) || 'normal'; return ((CAT && CAT.parole && CAT.parole[p]) ?? 180) * 1000; };
  function choisir(l) { l = (l || []).filter(Boolean); if (!l.length) return null; const fr = l.filter(x => Date.now() - (DITS.get(x) || 0) > 30 * 60000); const x = (fr.length ? fr : l)[(Math.random() * (fr.length ? fr : l).length) | 0]; DITS.set(x, Date.now()); return x; }
  // titre de tâche, de commit ou nom de poste : jamais répétés par l'hôte s'ils ne passent pas le filtre
  const DEFAUTS_JETONS = { fr: { nom: 'l’équipe', tache: 'sa tâche', titre: 'une nouvelle étape' }, en: { nom: 'the team', tache: 'the task', titre: 'a new step' } };
  function jetonsPropres(d) { const o = {}, df = DEFAUTS_JETONS[LANGUE] || DEFAUTS_JETONS.fr; for (const k of Object.keys(d || {})) { const v = String(d[k] == null ? '' : d[k]); o[k] = v.trim() && !filtrer(v).length ? v : (df[k] || '…'); } return o; }
  const remplir = (s, d) => String(s || '').replace(/\{(\w+)\}/g, (m, k) => d && d[k] != null ? String(d[k]) : m);
  // spontanée : une par intervalle au plus (Réglages : souvent, de temps en temps, rarement, jamais) ; force : vrai événement du studio
  function dire(texte, sec = 6, force) {
    if (!texte || !H || !permis() || intervalle() === 0) return false;
    if (!force && Date.now() - DERNIER < intervalle()) return false;
    const tel = typeof MODE_APP === 'function' && MODE_APP(); if (Bureau.bulles('hote') >= (tel ? 1 : 3)) return false;   // téléphone : jamais plus de 2 bulles
    DERNIER = Date.now(); Bureau.dire('hote', texte, sec); return true;
  }
  function repondre(id, ok) { if (!ok || !CAT) return; setTimeout(() => { if (!permis()) return; const r = choisir((CAT.reponses_collegues || {})[LANGUE] || CAT.reponses_collegues.fr); if (r && Bureau.bulles(id) < 3) Bureau.dire(id, r, 4.5); }, 3300); }

  // ------------------------------------------------------------------ sons (très discrets ; son coupé, mode absent, onglet caché, réglage de l'hôte)
  const sonsOk = () => !!(H && (!H.reglages || H.reglages.sons !== false) && !Son.coupe() && !document.hidden && !(typeof modeAbsent === 'function' && modeAbsent()) && CONF.mode === 'travail');
  const SONS_T = {};
  function bruit(d, o = {}) {
    const ctx = Son.contexte(); if (!ctx || !sonsOk()) return;
    try {
      const at = ctx.currentTime + (o.at || 0), n = Math.floor(ctx.sampleRate * d), b = ctx.createBuffer(1, n, ctx.sampleRate), x = b.getChannelData(0);
      for (let i = 0; i < n; i++) x[i] = (Math.random() * 2 - 1) * Math.sin(Math.PI * i / n);
      const s = ctx.createBufferSource(), f = ctx.createBiquadFilter(), g = ctx.createGain(); s.buffer = b; f.type = o.type || 'bandpass'; f.frequency.setValueAtTime(o.f || 1200, at);
      if (o.f2) f.frequency.linearRampToValueAtTime(o.f2, at + d); f.Q.value = o.q || 1; g.gain.value = (o.gain || .006) * clamp(+LS.get('son_vol', 1), 0, 1);
      s.connect(f).connect(g).connect(ctx.destination); s.start(at); s.stop(at + d + .02);
    } catch (e) { /* audio indisponible */ }
  }
  const note = (f, d, o = {}) => { if (sonsOk()) Son.bip(f, d, Object.assign({ gain: .006 }, o)); };
  const place = (k, ms) => { const n = performance.now(); if (n - (SONS_T[k] || 0) < ms) return false; SONS_T[k] = n; return true; };
  const S = {
    pas() { if (place('pas', 260)) bruit(.07, { type: 'lowpass', f: 520, gain: .007 }); },
    verse() { if (!place('verse', 3000)) return; bruit(1.6, { f: 1400, f2: 2200, q: 2, gain: .01 }); for (let i = 0; i < 6; i++) note(900 + Math.random() * 600, .05, { gain: .003, at: .3 + i * .22 }); },
    tasse() { if (place('tasse', 800)) { note(3100, .3, { gain: .006 }); note(4650, .2, { gain: .003, at: .005 }); } },
    arrose() { if (place('arrose', 3000)) bruit(1.8, { f: 3000, f2: 2300, q: 1.1, gain: .007, at: .15 }); },
    page() { if (place('page', 2500)) bruit(.18, { f: 2400, f2: 4200, q: .7, gain: .005 }); },
    crayon() { if (place('crayon', 600)) for (let i = 0; i < 3; i++) bruit(.05, { type: 'highpass', f: 3800, gain: .003, at: i * .09 }); },
    carton() { if (place('carton', 1500)) { bruit(.12, { type: 'lowpass', f: 380, gain: .012 }); note(120, .12, { gain: .006 }); } },
    air() { if (!place('air', 9000)) return; [523, 659, 784, 659, 587, 523].forEach((f, i) => note(f, .32, { type: 'triangle', gain: .0045, at: i * .34 })); },
    fauteuil() { if (place('fauteuil', 4000)) bruit(.22, { type: 'lowpass', f: 300, gain: .006 }); }
  };

  // ------------------------------------------------------------------ vie dans la scène
  const P = { x: null, y: null, ang: Math.PI / 4, dist: 0, marche: false, t: 0, arrivee: 0, depart: null };
  let ACT = null; const COOL = {}; let TEXTE = '';
  const dureeDe = { repos: 50, lit: 75, fenetre: 40, boisson: 120, arrose: 30, tournee: 30, musique: 45, range: 60, carnet: 55 };
  const COOLS = { boisson: 6, arrose: 10, musique: 8, tournee: 3, range: 6 };
  function siege() { const c = coin(); return { x: c.siege[0], y: c.siege[1], ang: 0, assis: true }; }
  function libres() { const O = Bureau && window.__hoteOutils; return O ? O.postes().filter(p => { try { const e = O.etat(p); return e && !e._depart; } catch (e) { return false; } }) : []; }
  function nouvelle(type, data) {
    const now = Date.now(); ACT = { type, debut: now, fin: now + ((dureeDe[type] || 40) + Math.random() * 20) * 1000, etape: 0, data: data || {} };
    if ((type === 'boisson' || type === 'tournee') && !ACT.data.ids) {
      const l = libres().sort(() => Math.random() - .5).map(p => p.id); ACT.data.ids = l.slice(0, type === 'boisson' ? 3 : 1);
      if (!ACT.data.ids.length) ACT.type = type === 'boisson' ? 'repos' : 'lit';
    }
    if (type === 'range' && !ACT.data.pts) { const O = window.__hoteOutils, pal = O ? O.palier() : 1; ACT.data.pts = (O ? O.COINS_LOISIR : []).filter(c => pal >= c.de && pal <= c.a).sort(() => Math.random() - .5).slice(0, 2).map(c => [c.gx, c.gy]); }
    if (type === 'carnet' && !ACT.data.pt) { const O = window.__hoteOutils, pal = O ? O.palier() : 1, l = (O ? O.COINS_LOISIR : []).filter(c => pal >= c.de && pal <= c.a); const c = l[(Math.random() * l.length) | 0]; ACT.data.pt = c ? [c.gx, c.gy] : null; }
    if (type === 'repos' && Math.random() < .3 && H && H.activites.includes('lit')) ACT.type = 'lit';
    return ACT;
  }
  function auHasard() {
    const poids = { repos: 3 }, now = Date.now();
    for (const a of (H.activites || [])) poids[a] = a === 'tournee' ? 1.2 : a === 'boisson' ? 1.6 : 1;
    for (const [k, m] of Object.entries(COOLS)) if (poids[k] && now - (COOL[k] || 0) < m * 60000) poids[k] = 0;
    const tot = Object.values(poids).reduce((a, b) => a + b, 0); let r = Math.random() * tot, type = 'repos';
    for (const [k, v] of Object.entries(poids)) { r -= v; if (r <= 0) { type = k; break; } }
    COOL[type] = now; return nouvelle(type);
  }
  const FILE = [];
  // ---- vrais événements du studio, relus toutes les 5 s : il réagit (bravo, encouragement, commit, décision, matin, soir)
  let BASE = null; const ECOOL = {};
  function veille() {
    if (!H || !CAT || CONF.mode !== 'travail' || typeof etatPoste !== 'function') return;
    const L0 = postes(), h = new Date().getHours(), dec = typeof decisionsOuvertes === 'function' ? decisionsOuvertes() : [];
    const e = { finis: new Set(L0.filter(p => { try { return etatPoste(p).etat === 'fini'; } catch (x) { return false; } }).map(p => p.id)),
      bloques: new Set(L0.filter(p => { try { return etatPoste(p).etat === 'bloque'; } catch (x) { return false; } }).map(p => p.id)),
      commit: (((ETAT && ETAT.git && ETAT.git.commits) || [])[0] || {}).hash || '', dec: new Set(dec.map(x => x.id)), per: h >= 6 && h < 10 ? 'matin' : h >= 21 || h < 4 ? 'soir' : 'jour' };
    if (!BASE) { BASE = e; return; }
    const annonce = (type, d, cible, ms) => { const now = Date.now(); if (now - (ECOOL[type] || 0) < ms) return; const s = choisir(repliques(type)); if (!s) return; ECOOL[type] = now; if (FILE.length >= 3) FILE.shift(); FILE.push({ type, texte: remplir(s, jetonsPropres(d)), cible }); };
    for (const id of e.finis) if (!BASE.finis.has(id)) { const p = L0.find(x => x.id === id) || {}; let tache = ''; try { tache = (etatPoste(p).ligne || {}).texte || ''; } catch (x) { /* rien */ } annonce('fini', { nom: nomPoste(p), tache: String(tache || (LANGUE === 'en' ? 'the task' : 'sa tâche')).slice(0, 60) }, id, 60000); }
    for (const id of e.bloques) if (!BASE.bloques.has(id)) { const p = L0.find(x => x.id === id) || {}; annonce('bloque', { nom: nomPoste(p) }, id, 600000); }
    if (e.commit && e.commit !== BASE.commit) { const c = ((ETAT.git.commits || [])[0]) || {}; annonce('commit', { titre: String(c.sujet || '').slice(0, 60) }, null, 480000); }
    for (const x of dec) if (!BASE.dec.has(x.id)) annonce('decision', {}, null, 300000);
    const jour = new Date().toISOString().slice(0, 10);
    if (e.per !== 'jour' && e.per !== BASE.per && LS.get('hote_' + e.per, '') !== jour) { LS.set('hote_' + e.per, jour); annonce(e.per, {}, null, 0); }
    BASE = e;
  }
  setInterval(() => { try { veille(); } catch (e) { /* rien */ } }, 5000);

  // objectif de l'instant : { x, y, ang, anim, assis, tenu, carton, cle }
  function objectif(now) {
    const c = coin(), s = siege();
    if (P.depart) return { x: P.depart.x, y: P.depart.y, ang: 0, anim: 'repos', cle: 'depart' };
    if (FILE.length && (!ACT || ['repos', 'lit', 'carnet', 'fenetre', 'musique'].includes(ACT.type) || now > ACT.fin)) { const f = FILE.shift(); nouvelle(f.cible ? 'annonce' : 'dit', f); ACT.fin = now + 25000; }
    else if (!ACT || now > ACT.fin) auHasard();
    const a = ACT, d = a.data, arrive = P.but && Math.hypot(P.x - P.but.x, P.y - P.but.y) < .05;
    const O = window.__hoteOutils, db = c.debout || [c.table[0], c.table[1] + .4], table = { x: db[0], y: db[1], ang: Math.atan2(c.table[1] - db[1], c.table[0] - db[0]) };
    switch (a.type) {
      case 'repos': if (arrive && !d.dit) { d.dit = true; S.fauteuil(); if (Math.random() < .45) dire(choisir(repliques(Math.random() < .5 ? 'coin' : 'spontanees')), 6); }
        return Object.assign(s, { anim: 'assis_boit', cle: 'coin' });
      case 'lit': if (arrive) { if (!d.dit) { d.dit = true; S.fauteuil(); if (Math.random() < .4) dire(choisir(repliquesActivite('lit')), 6); } if (Math.random() < .004) S.page(); }
        return Object.assign(s, { anim: 'tape', tenu: 'livre', cle: 'lit' });
      case 'dit': if (!d.fait) { d.fait = true; dire(d.texte, 7, true); a.fin = now + 9000; } return Object.assign(s, { anim: 'assis_boit', cle: 'coin' });
      case 'annonce': { const v = O && O.visite(d.cible); if (!v) { a.fin = 0; return Object.assign(s, { anim: 'assis_boit', cle: 'coin' }); }
        if (arrive && !d.fait) { d.fait = true; const ok = dire(d.texte, 8, true); repondre(d.cible, ok); a.fin = now + 9000; }
        return { x: v.x, y: v.y, ang: Math.atan2(v.sy - v.y, v.sx - v.x), anim: d.fait ? 'parle' : 'repos', cle: 'annonce' + d.cible }; }
      case 'fenetre': { const f = (O ? O.COINS_LOISIR : []).find(x => x.cle === 'fenetre') || { gx: 1.3, gy: 6.45, deg: 180 };
        if (arrive && !d.dit) { d.dit = true; dire(choisir(repliquesActivite('fenetre')), 6); }
        return { x: f.gx, y: f.gy, ang: f.deg * Math.PI / 180, anim: 'cafe_debout', cle: 'fenetre' }; }
      case 'arrose': { const i = (H.objets || []).filter(o => o !== 'tapis' && o !== 'radio').indexOf('plante'), pl = c.places[Math.max(0, i)] || c.places[0], bx = Math.min(15.7, pl[0] + .48), by = pl[1] + .08;   // à côté du pot, de profil : l'arrosoir se voit
        if (arrive && !d.dit) { d.dit = true; S.arrose(); dire(choisir(repliquesActivite('arrose')), 6); a.fin = now + 9000; d.eau = now; }
        return { x: bx, y: by, ang: Math.atan2(pl[1] - by, pl[0] - bx), anim: 'repos', tenu: 'arrosoir', eau: !!d.eau && now - d.eau < 6000, cle: 'arrose' }; }
      case 'musique': if (arrive && !d.dit) { d.dit = true; d.t0 = now; S.air(); dire(choisir(repliquesActivite('musique')), 6); }
        if (d.t0 && now - d.t0 > 8000 && now - d.t0 < 8200) S.air();
        return d.t0 && now - d.t0 > 7000 ? Object.assign(s, { anim: 'assis_boit', cle: 'coin', notes: true }) : Object.assign({}, table, { anim: 'joie', notes: !!d.t0, cle: 'radio' });
      case 'carnet': { const pt = d.pt || [c.siege[0] + .4, c.siege[1] + .5];
        if (arrive) { if (!d.dit) { d.dit = true; dire(choisir(repliquesActivite('carnet')), 6); } if (Math.random() < .01) S.crayon(); }
        return { x: pt[0], y: pt[1], ang: Math.atan2(6 - pt[1], 8 - pt[0]), anim: 'repos', tenu: 'carnet', cle: 'carnet' }; }
      case 'range': { const pts = d.pts || []; const pt = pts[a.etape];
        if (!pt) { a.fin = 0; return Object.assign(s, { anim: 'assis_boit', cle: 'coin' }); }
        if (arrive && P.but.cle === 'range' + a.etape) { if (!d['v' + a.etape]) { d['v' + a.etape] = now; S.carton(); if (a.etape === 0) dire(choisir(repliquesActivite('range')), 6); } else if (now - d['v' + a.etape] > 5000) a.etape++; }
        return { x: pt[0], y: pt[1], ang: Math.PI / 4, anim: 'repos', carton: true, cle: 'range' + a.etape }; }
      case 'boisson': case 'tournee': {
        if (a.type === 'boisson' && a.etape === 0) { if (arrive && P.but.cle === 'prend') { a.etape = 1; S.tasse(); } return Object.assign({}, table, { anim: 'repos', cle: 'prend' }); }
        const id = (d.ids || [])[a.type === 'boisson' ? a.etape - 1 : a.etape]; const v = id && O && O.visite(id);
        if (!v) { a.fin = 0; return Object.assign(s, { anim: 'assis_boit', cle: 'coin' }); }
        if (arrive && P.but.cle === 'v' + id) {
          if (!d['v' + id]) { d['v' + id] = now; const ok = dire(choisir(repliquesActivite(a.type)), 6); repondre(id, ok); if (a.type === 'boisson') S.verse(); }
          else if (now - d['v' + id] > 7000) a.etape++;
        }
        return { x: v.x, y: v.y, ang: Math.atan2(v.sy - v.y, v.sx - v.x), anim: arrive && d['v' + id] ? 'parle' : 'repos', tenu: a.type === 'boisson' ? 'theiere' : null, verse: a.type === 'boisson' && arrive && d['v' + id] && now - d['v' + id] < 3500, cle: 'v' + id };
      }
    }
    return Object.assign(s, { anim: 'assis_boit', cle: 'coin' });
  }
  function texteActivite() {
    if (!H) return '';
    if (P.depart) return t('ho_depart'); if (P.arrivee && P.marche && performance.now() - P.arrivee < 30000) return t('ho_arrivee');
    if (!ACT || ACT.type === 'repos' || ACT.type === 'dit') return t('ho_repos');
    if (ACT.type === 'annonce') { const p = postes().find(x => x.id === ACT.data.cible); return t('ho_vers') + ' ' + (p ? nomPoste(p) : ''); }
    const a = parId('activites', ACT.type); return a ? L(a.texte) : t('ho_repos');
  }

  // ------------------------------------------------------------------ dessin (outils du Bureau : studio.html, OUTILS_HOTE)
  function dessinerCoin(O, th, lien) {
    const c = coin(), [x0, y0, x1, y1] = c.r, cx = O.cx(), TW = O.TW(), lk = lookDeFiche(H) || {}, c1 = (lk.tenue || {}).couleur1 || '#3f7a52', c2 = (lk.tenue || {}).couleur2 || '#e9c47f';
    const objs = (H.objets || []), places = objs.filter(o => !['tapis', 'radio'].includes(o)), surTable = [];
    if (places.length > c.places.length) surTable.push(...places.splice(c.places.length));
    if (objs.includes('radio')) surTable.push('radio');
    const out = [];
    if (objs.includes('tapis')) out.push({ k: x0 + y0 - 9, f: () => {   // tapis : à plat sous le coin, bord et rayures aux couleurs de l'hôte
      const m = .08, q = [O.iso(x0 + m, y0 + m), O.iso(x1 - m, y0 + m), O.iso(x1 - m, y1 - m), O.iso(x0 + m, y1 - m)];
      O.poly(q, O.mix(c2, '#ffffff', .1), 'rgba(0,0,0,.15)'); const q2 = [O.iso(x0 + .18, y0 + .18), O.iso(x1 - .18, y0 + .18), O.iso(x1 - .18, y1 - .18), O.iso(x0 + .18, y1 - .18)]; O.poly(q2, null, O.mix(c1, '#000000', .1));
      cx.save(); cx.globalAlpha = .55; for (let i = 1; i < 6; i++) { const gx = x0 + .18 + (x1 - x0 - .36) * i / 6; O.poly([O.iso(gx - .03, y0 + .22), O.iso(gx + .03, y0 + .22), O.iso(gx + .03, y1 - .22), O.iso(gx - .03, y1 - .22)], c1); } cx.restore(); } });
    // fauteuil (dos au mur côté -x, il regarde +x) : dos et accoudoir du fond avant lui, accoudoir de devant après
    const [sx, sy] = c.siege, fc = O.mix(c1, '#3a2c22', .35);
    out.push({ k: sx + sy - .45, f: () => { O.boite(sx - .36, sy - .3, .14, .6, 1.25, O.mix(fc, '#000000', .1)); O.boite(sx - .3, sy - .32, .56, .1, .9, fc); O.boite(sx - .26, sy - .24, .52, .48, .62, O.mix(fc, '#ffffff', .12)); } });
    out.push({ k: sx + sy + .32, f: () => O.boite(sx - .3, sy + .22, .56, .1, .9, fc) });
    // guéridon : pied, plateau ; dessus : tasse, théière (sauf quand il la porte), radio, livres en trop
    const [tx, ty] = c.table;
    out.push({ k: tx + ty, f: () => {
      O.boite(tx - .03, ty - .03, .06, .06, .62, '#4a3a2c'); O.boite(tx - .19, ty - .19, .38, .38, .05, O.mix(th.bois || '#a0744a', '#ffffff', .1), .62);
      const [px, py] = O.iso(tx, ty, .67), u = TW / 64;
      if (!(ACT && ACT.type === 'boisson' && ACT.etape > 0)) theiere(cx, px - 5 * u, py - 2 * u, u * .8, c1);
      cx.fillStyle = '#f4ecd9'; cx.fillRect(px + 4 * u, py - 5 * u, 4 * u, 4 * u); cx.strokeStyle = 'rgba(0,0,0,.25)'; cx.lineWidth = .7; cx.strokeRect(px + 4 * u, py - 5 * u, 4 * u, 4 * u);
      if (surTable.includes('radio')) radio(O, tx - .02, ty + .12, .67, c1);
      if (surTable.includes('livres')) livres(O, tx + .1, ty - .12, .67, 2);
      if (ACT && ACT.type === 'musique' || (P.cible && P.cible.notes)) notes(cx, ...O.iso(tx, ty + .12, 1.0), u);
    } });
    places.forEach((o, i) => { const [ox, oy] = c.places[i]; out.push({ k: ox + oy, f: () => objet(O, o, ox, oy, c1, c2) }); });
    return out;
  }
  function objet(O, o, x, y, c1, c2) {
    const cx = O.cx(), TW = O.TW(), u = TW / 64;
    if (o === 'plante') { O.boite(x - .14, y - .14, .28, .28, .34, '#a8432e'); const [px, py] = O.iso(x, y, .34), v = Math.sin(performance.now() / 1400 + x) * .05;
      for (let i = 0; i < 9; i++) { const a = -Math.PI / 2 + (i - 4) * .33 + v; cx.fillStyle = O.mix('#3f7a52', '#7fae5e', (i % 3) / 3); cx.beginPath(); cx.ellipse(px + Math.cos(a) * 9 * u, py - 6 * u + Math.sin(a) * 11 * u, 8 * u, 3.4 * u, a, 0, 7); cx.fill(); }
      if (ACT && ACT.type === 'arrose' && P.cible && P.cible.eau) { cx.fillStyle = 'rgba(140,190,230,.8)'; for (let i = 0; i < 4; i++) { const k = ((performance.now() / 500 + i / 4) % 1); cx.beginPath(); cx.arc(px + (i - 1.5) * 3 * u, py - 14 * u + k * 12 * u, 1.2 * u, 0, 7); cx.fill(); } } }
    else if (o === 'lampe') { O.boite(x - .1, y - .1, .2, .2, .05, '#3a3128'); const [bx, by] = O.iso(x, y, .05), [hx, hy] = O.iso(x, y, 1.9);
      cx.strokeStyle = '#3a3128'; cx.lineWidth = 2 * u; cx.beginPath(); cx.moveTo(bx, by); cx.lineTo(hx, hy); cx.stroke();
      const nuit = O.nuit(); if (nuit) { const g = cx.createRadialGradient(hx, hy + 6 * u, 1, hx, hy + 6 * u, 70 * u); g.addColorStop(0, 'rgba(255,214,140,.32)'); g.addColorStop(1, 'rgba(255,214,140,0)'); cx.fillStyle = g; cx.beginPath(); cx.arc(hx, hy + 6 * u, 70 * u, 0, 7); cx.fill(); }
      cx.fillStyle = nuit ? '#ffe2a8' : O.mix(c2, '#ffffff', .2); cx.beginPath(); cx.moveTo(hx - 7 * u, hy + 4 * u); cx.lineTo(hx + 7 * u, hy + 4 * u); cx.lineTo(hx + 4.5 * u, hy - 6 * u); cx.lineTo(hx - 4.5 * u, hy - 6 * u); cx.closePath(); cx.fill(); cx.strokeStyle = 'rgba(0,0,0,.2)'; cx.lineWidth = .8; cx.stroke(); }
    else if (o === 'livres') livres(O, x, y, 0, 4);
    else if (o === 'aquarium') { O.boite(x - .26, y - .14, .52, .28, .42, '#4a3a2c'); const z = .42; O.boite(x - .25, y - .13, .5, .26, .36, 'rgba(150,200,225,.55)', z);
      const [ax, ay] = O.iso(x, y, z + .18), tt = performance.now() / 1000; for (let i = 0; i < 3; i++) { const fx = ax + Math.sin(tt * (.6 + i * .2) + i * 2) * 9 * u, fy = ay - 3 * u + i * 3 * u; cx.fillStyle = ['#e2803a', '#e2b866', '#d77b62'][i]; cx.beginPath(); cx.ellipse(fx, fy, 2.4 * u, 1.3 * u, 0, 0, 7); cx.fill(); }
      cx.fillStyle = 'rgba(255,255,255,.7)'; for (let i = 0; i < 3; i++) { const k = (tt * .4 + i / 3) % 1; cx.beginPath(); cx.arc(ax + 6 * u, ay + 6 * u - k * 16 * u, .9 * u, 0, 7); cx.fill(); } }
    else if (o === 'radio') radio(O, x, y, 0, c1);
  }
  function livres(O, x, y, z, n) { const cols = ['#a8432e', '#4d6f9c', '#3f7a52', '#c9953e', '#6a4a7c']; for (let i = 0; i < n; i++) O.boite(x - .13 + (i % 2) * .02, y - .09, .26, .18, .055, cols[i % cols.length], z + i * .055); }
  function radio(O, x, y, z, c1) { const cx = O.cx(), u = O.TW() / 64; O.boite(x - .13, y - .08, .26, .16, .17, O.mix(c1, '#6e5130', .5), z); const [ax, ay] = O.iso(x + .1, y - .05, z + .17); cx.strokeStyle = '#2b241c'; cx.lineWidth = u; cx.beginPath(); cx.moveTo(ax, ay); cx.lineTo(ax + 6 * u, ay - 12 * u); cx.stroke(); const [dx, dy] = O.iso(x, y + .08, z + .09); cx.fillStyle = '#f4ecd9'; cx.beginPath(); cx.arc(dx, dy, 2 * u, 0, 7); cx.fill(); }
  function notes(cx, x, y, u) { const tt = performance.now() / 1000; cx.save(); cx.font = `${Math.round(11 * u)}px serif`; cx.fillStyle = '#5c4f3f'; for (let i = 0; i < 3; i++) { const k = (tt * .35 + i / 3) % 1; cx.globalAlpha = Math.sin(k * Math.PI) * .8; cx.fillText(i % 2 ? '♫' : '♪', x + Math.sin(k * 6 + i) * 6 * u, y - k * 26 * u); } cx.restore(); }
  function theiere(cx, x, y, u, c1) { cx.save(); cx.fillStyle = c1; cx.strokeStyle = 'rgba(0,0,0,.35)'; cx.lineWidth = .8; cx.beginPath(); cx.ellipse(x, y, 5 * u, 4 * u, 0, 0, 7); cx.fill(); cx.stroke(); cx.beginPath(); cx.moveTo(x + 4 * u, y - u); cx.lineTo(x + 8.5 * u, y - 4.5 * u); cx.lineWidth = 1.6 * u; cx.strokeStyle = c1; cx.stroke(); cx.beginPath(); cx.arc(x - 5.2 * u, y - .5 * u, 2.4 * u, Math.PI * .5, Math.PI * 1.5); cx.lineWidth = 1.1 * u; cx.stroke(); cx.fillStyle = '#e9e1cf'; cx.beginPath(); cx.arc(x, y - 4 * u, 1.3 * u, 0, 7); cx.fill(); cx.restore(); }
  function tenu(O, q, x, y, h) {   // objet tenu à la main (ancres des mains du sprite, sinon une place approchée)
    const cx = O.cx(), u = O.TW() / 64, sp = window.SpritesPerso && SpritesPerso.dernier, md = (sp && sp.mainD) || [x + 7 * u, y - h * .45], mg = (sp && sp.mainG) || [x - 7 * u, y - h * .45];
    const lk = lookDeFiche(H) || {}, c1 = (lk.tenue || {}).couleur1 || '#3f7a52';
    if (q.tenu === 'theiere') { theiere(cx, md[0] + 2 * u, md[1] + 2 * u, u * .9, c1); if (q.verse) { cx.strokeStyle = 'rgba(176,120,60,.75)'; cx.lineWidth = 1.2 * u; cx.beginPath(); cx.moveTo(md[0] + 9.5 * u, md[1] - 1 * u); cx.quadraticCurveTo(md[0] + 13 * u, md[1] + 6 * u, md[0] + 12 * u, md[1] + 16 * u); cx.stroke(); } }
    else if (q.tenu === 'arrosoir') { cx.save(); cx.fillStyle = '#7d8a96'; cx.fillRect(md[0] - 3 * u, md[1] - 1 * u, 8 * u, 6 * u); cx.strokeStyle = '#7d8a96'; cx.lineWidth = 1.6 * u; cx.beginPath(); cx.moveTo(md[0] + 5 * u, md[1] + u); cx.lineTo(md[0] + 11 * u, md[1] - 3 * u); cx.stroke(); cx.restore();
      if (q.eau) { cx.fillStyle = 'rgba(140,190,230,.85)'; for (let i = 0; i < 4; i++) { const k = ((performance.now() / 420 + i / 4) % 1); cx.beginPath(); cx.arc(md[0] + 11 * u + k * 2 * u, md[1] - 3 * u + k * 14 * u, 1 * u, 0, 7); cx.fill(); } } }
    else if (q.tenu === 'livre' || q.tenu === 'carnet') { const mx = (md[0] + mg[0]) / 2, my = (md[1] + mg[1]) / 2 - 2 * u, w = q.tenu === 'livre' ? 7 : 5;
      cx.save(); cx.fillStyle = q.tenu === 'livre' ? '#f4ecd9' : '#fffdf6'; cx.strokeStyle = q.tenu === 'livre' ? '#a8432e' : '#5c4f3f'; cx.lineWidth = 1.1 * u; cx.beginPath(); cx.moveTo(mx, my + 2 * u); cx.lineTo(mx - w * u, my); cx.lineTo(mx - w * u, my - 6 * u); cx.lineTo(mx, my - 4 * u); cx.lineTo(mx + w * u, my - 6 * u); cx.lineTo(mx + w * u, my); cx.closePath(); cx.fill(); cx.stroke();
      if (q.tenu === 'carnet') { cx.strokeStyle = '#c9953e'; cx.lineWidth = 1.2 * u; cx.beginPath(); cx.moveTo(md[0], md[1]); cx.lineTo(md[0] + 4 * u, md[1] - 6 * u); cx.stroke(); } cx.restore(); }
  }
  // déplacement vers l'objectif (ligne droite, comme l'assistant), pas feutrés
  function bouger(now, dt, O) {
    const c = coin();
    if (P.x === null) { P.x = c.siege[0]; P.y = c.siege[1]; }
    const q = objectif(now); P.cible = q;
    if (!P.but || P.but.cle !== q.cle || Math.hypot(P.but.x - q.x, P.but.y - q.y) > .01) P.but = { x: q.x, y: q.y, cle: q.cle };
    const dx = q.x - P.x, dy = q.y - P.y, d = Math.hypot(dx, dy), v = (P.depart || (ACT && ACT.type === 'annonce') ? 1.5 : 1.1) * dt;
    if (d > .02 && O.ANIM()) { const pas = Math.min(v, d); P.x += dx / d * pas; P.y += dy / d * pas; P.ang = Math.atan2(dy, dx); P.dist += pas; P.marche = true; if (Math.floor(P.dist / .45) !== P._pas) { P._pas = Math.floor(P.dist / .45); S.pas(); } }
    else { P.marche = false; if (!O.ANIM()) { P.x = q.x; P.y = q.y; } P.ang = q.ang; }
  }
  let T_PREC = 0;
  function objets(O, th) {
    window.__hoteOutils = O;
    if (!H || !CAT || CONF.mode !== 'travail') return [];
    const now = Date.now(), n = performance.now(), dt = T_PREC ? clamp((n - T_PREC) / 1000, 0, .2) : 0; T_PREC = n;
    bouger(now, dt, O);
    if (P.depart && Math.hypot(P.x - P.depart.x, P.y - P.depart.y) < .1) { const fin = P.depart.fin; P.depart = null; H = null; ACT = null; P.x = null; FILE.length = 0; if (fin) fin(); return []; }
    const out = dessinerCoin(O, th), look = lookDeFiche(H), q = P.cible || {};
    const assis = !P.marche && q.assis, anim = P.marche ? 'marche' : (q.anim || 'repos');
    out.push({ k: P.x + P.y + (assis ? 0 : .02), f: () => {
      if (window.SpritesPerso) SpritesPerso.dernier = null;
      const [x, y, h] = O.perso(P.x, P.y, look, { anim, ang: P.ang, dist: P.dist / O.S_PERSO, seed: 2.7, ombre: !assis }, { marche: P.marche, cligne: true, assis, carton: !!q.carton, tasse: !P.marche && ['assis_boit', 'cafe_debout'].includes(anim) });
      if (q.tenu && !(P.marche && q.tenu === 'livre')) tenu(O, q, x, y, h);
      P.monde = [x, y - h * .55]; const TW = O.TW(); O.ZONES.push({ x: x - TW * .4, y: y - h, w: TW * .8, h: h + TW * .1, f: () => ouvrirFiche(), perso: 1, sid: 'hote' });
    } });
    return out;
  }
  const present = () => (H && !P.depart ? H : null);   // l'hôte installé (pas celui qui repart par la porte)
  function changement(avant, apres) {
    if (PREMIER) { P.x = null; return; }
    const O = window.__hoteOutils;
    if (apres) P.depart = null;   // un hôte (re)créé pendant que l'ancien sortait : celui-ci reste
    if (!avant && apres) {   // nouvel hôte : il entre par la porte et va dans son coin
      const pt = (O && O.PORTE) || [.6, 9.85]; P.x = pt[0]; P.y = pt[1]; P.arrivee = performance.now(); ACT = null; nouvelle('repos'); ACT.fin = Date.now() + 60000;
      const c = parId('coins', apres.coin); toast(`<b>${esc(apres.nom)}</b><br>${esc(tf('ho_arrive', { n: apres.nom, c: c ? L(c.nom).toLowerCase() : '' }))}`, { duree: 6000 });
      try { Son.succes('petit'); } catch (e) { /* rien */ }
      setTimeout(() => dire(choisir(repliques('coin')) || (LANGUE === 'en' ? 'Hello everyone!' : 'Bonjour tout le monde !'), 6, true), 9000);
    } else if (avant && apres && avant.nom !== apres.nom) { Bureau.taire('hote'); FILE.length = 0; ACT = null;   // un autre hôte : rien de ce que disait l'ancien
    } else if (avant && !apres) {   // supprimé : il repart par la porte avec sa fiche
      if (O && P.x !== null) { H = avant; const pt = O.PORTE || [.6, 9.85]; P.depart = { x: pt[0], y: pt[1], fin: () => {} }; Bureau.taire('hote'); dire(LANGUE === 'en' ? 'Bye everyone!' : 'Au revoir tout le monde !', 4, true); }
    }
  }

  // ------------------------------------------------------------------ création
  const C = { mode: null, etape: 0, ch: {} };
  const ETAPES = ['allure', 'couleurs', 'accessoire', 'coin', 'activites', 'objets', 'ton', 'nom'];
  function choixDepuis(f) {
    const lk = lookDeFiche(f) || {}, ten = lk.tenue || {};
    const coul = (CAT.couleurs.find(c => c.couleur1 === ten.couleur1) || {}).id || f.couleurs || null;
    return { allure: f.allure || null, look: f.look || null, couleurs: coul, accessoire: lk.accessoire || 'aucun', coin: f.coin, activites: (f.activites || []).slice(), objets: (f.objets || []).filter(o => !(CAT.activites || []).some(a => a.objet_requis === o && (f.activites || []).includes(a.id))).slice(0, 3), ton: f.ton, ton0: f.ton, nom: f.nom || '', repliques: f.repliques || null, source: f.source, prompt: f.prompt };
  }
  function lookChoix(ch, sur) {
    const base = ch.look && !sur ? JSON.parse(JSON.stringify(ch.look)) : JSON.parse(JSON.stringify((parId('allures', (sur && sur.allure) || ch.allure) || CAT.allures[0]).look));
    const c = parId('couleurs', (sur && sur.couleurs) || ch.couleurs); base.tenue = Object.assign({}, base.tenue || {}, c ? { couleur1: c.couleur1, couleur2: c.couleur2 } : (ch.look && ch.look.tenue) || {});
    base.accessoire = (sur && sur.accessoire) || ch.accessoire || base.accessoire || 'aucun'; return base;
  }
  function creer(depuis) {
    if (!CAT) { charger().then(() => CAT && creer(depuis)); return; }
    const f = depuis || H;
    if (f) { C.mode = 'choix'; C.etape = 0; C.ch = choixDepuis(f); }
    else { C.mode = null; C.etape = 0; C.ch = { activites: [], objets: [], accessoire: 'aucun' }; }
    if (!f && PROP && PROP.statut === 'en_attente') C.mode = 'attente';
    if (!f && PROP && PROP.statut === 'prete') C.mode = 'apercu';
    rendre();
  }
  function rendre() { Panneau.remplacer('hote', el => vue(el)); }
  function vue(el) {
    const tete = `<div class="surtitre">${esc(t('ho_fiche_sur'))}</div>`;
    if (!C.mode) {
      el.innerHTML = `${tete}<h2>${esc(t('ho_titre'))}</h2><p>${esc(t('ho_intro'))}</p>
        <div class="ho-deux"><button type="button" class="ho-carte" data-mode="choix"><img class="ho-ic" src="cartes/carnet.svg" alt=""><b>${esc(t('ho_par_choix'))}</b><small>${esc(t('ho_par_choix_d'))}</small></button>
        <button type="button" class="ho-carte" data-mode="prompt"><img class="ho-ic" src="cartes/plume.svg" alt=""><b>${esc(t('ho_par_prompt'))}</b><small>${esc(t('ho_par_prompt_d'))}</small></button></div>`;
      el.querySelectorAll('[data-mode]').forEach(b => b.onclick = () => { Son.clic(); C.mode = b.dataset.mode; C.etape = 0; vue(el); });
      return;
    }
    if (C.mode === 'prompt') return vuePrompt(el, tete);
    if (C.mode === 'attente') return vueAttente(el, tete);
    if (C.mode === 'apercu') return vueApercu(el, tete);
    vueEtape(el, tete);
  }
  // portrait rendu (sprites du skill) ; tant qu'une planche n'est pas chargée, dessin de repli puis nouvel essai
  function portrait(canvas, look, n = 0) { try { if (window.SpritesPerso && SpritesPerso.portrait(canvas, look)) return; Bureau.portrait(canvas, look); if (n < 8 && canvas.isConnected !== false) setTimeout(() => portrait(canvas, look, n + 1), 350); } catch (e) { /* rien */ } }
  function vueEtape(el, tete) {
    const ch = C.ch, e = ETAPES[C.etape], pas = ETAPES.map((x, i) => `<i class="${i <= C.etape ? 'on' : ''}"></i>`).join('');
    let corps = '', aide = '';
    if (e === 'allure') corps = CAT.allures.map(a => `<button type="button" class="ho-carte${ch.allure === a.id && !ch.look ? ' choisie' : ''}" data-v="${esc(a.id)}"><canvas width="192" height="192" data-look='${esc(JSON.stringify(lookChoix(ch, { allure: a.id })))}'></canvas>${esc(L(a.nom))}</button>`).join('');
    else if (e === 'couleurs') corps = CAT.couleurs.map(c => `<button type="button" class="ho-carte${ch.couleurs === c.id ? ' choisie' : ''}" data-v="${esc(c.id)}"><canvas width="192" height="192" data-look='${esc(JSON.stringify(lookChoix(ch, { couleurs: c.id })))}'></canvas><span class="ho-nuancier"><i style="background:${esc(c.couleur1)}"></i><i style="background:${esc(c.couleur2)}"></i></span>${esc(L(c.nom))}</button>`).join('');
    else if (e === 'accessoire') corps = CAT.accessoires.map(a => `<button type="button" class="ho-carte${(ch.accessoire || 'aucun') === a ? ' choisie' : ''}" data-v="${esc(a)}"><canvas width="192" height="192" data-look='${esc(JSON.stringify(lookChoix(ch, { accessoire: a })))}'></canvas>${esc(t('pe_' + a) === 'pe_' + a ? a.replace(/_/g, ' ') : t('pe_' + a))}</button>`).join('');
    else if (e === 'coin') corps = CAT.coins.map(c => `<button type="button" class="ho-carte${ch.coin === c.id ? ' choisie' : ''}" data-v="${esc(c.id)}"><canvas width="192" height="144" data-coin="${esc(c.id)}"></canvas>${esc(L(c.nom))}</button>`).join('');
    else if (e === 'activites') { aide = `${tf('ho_choisis', { n: '3–4' })}`; corps = CAT.activites.map(a => `<button type="button" class="ho-carte${ch.activites.includes(a.id) ? ' choisie' : ''}" data-v="${esc(a.id)}" aria-pressed="${ch.activites.includes(a.id)}">${icone(a.id)}${esc(L(a.nom))}${a.objet_requis ? `<small>+ ${esc(L((parId('objets', a.objet_requis) || {}).nom))}</small>` : ''}</button>`).join(''); }
    else if (e === 'objets') { aide = tf('ho_choisis_max', { n: 3 }); const req = CAT.activites.filter(a => ch.activites.includes(a.id) && a.objet_requis);
      corps = CAT.objets.map(o => { const r = req.find(a => a.objet_requis === o.id); return `<button type="button" class="ho-carte${ch.objets.includes(o.id) || r ? ' choisie' : ''}" data-v="${esc(o.id)}"${r ? ' disabled' : ''}>${icone(o.id)}${esc(L(o.nom))}${r ? `<small>${esc(tf('ho_apporte', { a: L(r.nom) }))}</small>` : ''}</button>`; }).join(''); }
    else if (e === 'ton') corps = CAT.tons.map(o => `<button type="button" class="ho-carte${ch.ton === o.id ? ' choisie' : ''}" data-v="${esc(o.id)}">${icone(o.id)}<b>${esc(L(o.nom))}</b><small class="ho-cite">« ${esc(L(o.exemple))} »</small></button>`).join('');
    const nomV = e === 'nom';
    el.innerHTML = `${tete}<h2>${esc(t('ho_e_' + e))}</h2><div class="ho-pas">${pas}</div>${aide ? `<p class="discret">${esc(aide)}</p>` : ''}
      ${nomV ? `<div class="ho-tete"><canvas width="240" height="240" id="ho-final"></canvas><div style="flex:1"><label class="reglage" style="display:block">${esc(t('ho_e_nom'))}<br><input type="text" id="ho-nom" maxlength="30" style="width:100%;font-size:16px;padding:8px;border-radius:8px;border:1px solid rgba(92,79,63,.3)" placeholder="${esc(t('ho_nom_ph'))}" value="${esc(ch.nom || '')}"></label><div class="ho-erreur" id="ho-err"></div>${recapHTML(ch)}</div></div>` : `<div class="ho-grille">${corps}</div>`}
      <div class="rangee" style="margin-top:14px"><button type="button" class="bts" data-nav="retour">${esc(t('ho_retour'))}</button>${C.etape === 0 ? `<button type="button" class="bts" data-nav="hasard">🎲 ${esc(t('ho_hasard'))}</button>` : ''}
      <button type="button" class="btp" data-nav="suivant"${valide(e) ? '' : ' disabled'}>${esc(nomV ? t('ho_installer') : t('ho_suivant'))}</button><span class="discret" data-res></span></div>`;
    el.querySelectorAll('canvas[data-look]').forEach(c => { try { portrait(c, JSON.parse(c.dataset.look)); } catch (x) { /* rien */ } });
    el.querySelectorAll('canvas[data-coin]').forEach(c => plan(c, c.dataset.coin));
    if (nomV) { portrait(el.querySelector('#ho-final'), lookChoix(ch)); const i = el.querySelector('#ho-nom'), err = el.querySelector('#ho-err'), ok = el.querySelector('[data-nav="suivant"]');
      const maj = () => { ch.nom = i.value; const f = filtrer(i.value); err.textContent = f.length ? t('ho_filtre') : ''; ok.disabled = !valide('nom'); }; i.oninput = maj; maj(); }
    el.querySelectorAll('.ho-carte[data-v]').forEach(b => b.onclick = () => {
      Son.clic(); const v = b.dataset.v;
      if (e === 'allure') { ch.allure = v; ch.look = null; } else if (e === 'couleurs') { ch.couleurs = v; if (ch.look) ch.look = null; } else if (e === 'accessoire') ch.accessoire = v; else if (e === 'coin') ch.coin = v; else if (e === 'ton') ch.ton = v;
      else if (e === 'activites') { const i = ch.activites.indexOf(v); if (i >= 0) ch.activites.splice(i, 1); else if (ch.activites.length < 4) ch.activites.push(v); }
      else if (e === 'objets') { const i = ch.objets.indexOf(v); if (i >= 0) ch.objets.splice(i, 1); else if (ch.objets.length < 3) ch.objets.push(v); }
      vueEtape(el, tete);
    });
    el.querySelectorAll('[data-nav]').forEach(b => b.onclick = async () => {
      Son.clic(); const n = b.dataset.nav;
      if (n === 'retour') { if (C.etape === 0) { C.mode = C.ch.source === 'prompt' && PROP ? 'apercu' : null; } else C.etape--; return vue(el); }
      if (n === 'hasard') { const r = l => l[(Math.random() * l.length) | 0], m = l => l.slice().sort(() => Math.random() - .5);
        Object.assign(ch, { allure: r(CAT.allures).id, look: null, couleurs: r(CAT.couleurs).id, accessoire: r(CAT.accessoires), coin: r(CAT.coins).id, activites: m(CAT.activites.map(a => a.id)).slice(0, 3 + (Math.random() < .5)), objets: m(CAT.objets.map(o => o.id)).slice(0, 2), ton: r(CAT.tons).id }); C.etape = ETAPES.length - 1; return vue(el); }
      if (!valide(e)) return;
      if (!nomV) { C.etape++; return vue(el); }
      b.disabled = true; const res = el.querySelector('[data-res]');
      try { const r = await poster('/api/hote', { action: 'creer', fiche: ficheChoix(ch) }); H = null; SIG_H = ''; Panneau.fermer(); setTimeout(charger, 200); if (r.avertissements && r.avertissements.length) toast(esc(t('ho_avert')) + ' : ' + esc(r.avertissements.join(' ; ')), { duree: 5000 }); }
      catch (x) { res.textContent = x.message; b.disabled = false; }
    });
  }
  function valide(e) {
    const ch = C.ch;
    return e === 'allure' ? !!(ch.allure || ch.look) : e === 'couleurs' ? !!(ch.couleurs || ch.look) : e === 'accessoire' ? true : e === 'coin' ? !!parId('coins', ch.coin)
      : e === 'activites' ? ch.activites.length >= 3 && ch.activites.length <= 4 : e === 'objets' ? ch.objets.length <= 3 : e === 'ton' ? !!parId('tons', ch.ton)
      : e === 'nom' ? !!String(ch.nom || '').trim() && !filtrer(ch.nom).length : false;
  }
  function ficheChoix(ch) {
    const f = { nom: String(ch.nom || '').trim(), coin: ch.coin, activites: ch.activites, objets: ch.objets, ton: ch.ton, look: lookChoix(ch), source: ch.source === 'prompt' ? 'prompt' : 'choix', reglages: (H && H.reglages) || { sons: true, parole: 'normal' } };
    if (ch.allure) f.allure = ch.allure; if (ch.couleurs) f.couleurs = ch.couleurs;
    if (ch.repliques && ch.ton === ch.ton0) { f.repliques = ch.repliques; if (ch.prompt) f.prompt = ch.prompt; } else f.source = 'choix';   // autre ton : ses répliques à lui ne collent plus
    return f;
  }
  function recapHTML(f) {
    const c = parId('coins', f.coin), to = parId('tons', f.ton);
    return `<ul class="ho-liste"><li><b>${esc(t('ho_coin'))}</b> : ${esc(L(c && c.nom))}</li><li><b>${esc(t('ho_activites'))}</b> : ${esc((f.activites || []).map(a => L((parId('activites', a) || {}).nom)).join(', '))}</li>
      ${(f.objets || []).length ? `<li><b>${esc(t('ho_e_objets').replace(/\s*\(.*\)$/, ''))}</b> : ${esc(f.objets.map(o => L((parId('objets', o) || {}).nom)).join(', '))}</li>` : ''}<li><b>${esc(t('ho_ton'))}</b> : ${esc(L(to && to.nom))}</li></ul>`;
  }
  // plan miniature du studio : la pièce, les bureaux, le coin choisi en couleur
  function plan(canvas, id) {
    const c = canvas.getContext('2d'), W = canvas.width, Hh = canvas.height, k = Math.min(W / 17, Hh / 13), ox = (W - 16 * k) / 2, oy = (Hh - 12 * k) / 2, O = window.__hoteOutils;
    c.clearRect(0, 0, W, Hh); c.fillStyle = '#e9dcc0'; c.fillRect(ox, oy, 16 * k, 12 * k); c.strokeStyle = '#8a7b66'; c.lineWidth = 2; c.strokeRect(ox, oy, 16 * k, 12 * k);
    c.fillStyle = '#b8a283'; if (O) O.postes().forEach(p => { const v = O.visite(p.id); if (v) c.fillRect(ox + (v.sx - .7) * k, oy + (v.sy - 1.05) * k, 1.5 * k, .75 * k); });
    c.fillStyle = '#6e5130'; c.fillRect(ox - 2, oy + 9.2 * k, 4, 1.4 * k);   // porte
    for (const x of CAT.coins) { const [x0, y0, x1, y1] = x.r; c.fillStyle = x.id === id ? '#c9953e' : 'rgba(92,79,63,.18)'; c.fillRect(ox + x0 * k, oy + y0 * k, (x1 - x0) * k, (y1 - y0) * k); }
  }
  function vuePrompt(el, tete) {
    el.innerHTML = `${tete}<h2>${esc(t('ho_prompt_t'))}</h2><p class="discret">${esc(t('ho_prompt_aide'))}</p>
      <textarea class="ho-zone" id="ho-prompt" maxlength="600" placeholder="${esc(t('ho_prompt_ph'))}">${esc(C.prompt || '')}</textarea>
      <div class="rangee" style="margin-top:4px">${typeof boutonMicro === 'function' ? boutonMicro('#ho-prompt') : ''}<span class="ho-erreur" id="ho-err"></span></div>
      <div class="surtitre" style="margin-top:8px">${esc(t('ho_exemples'))}</div>${['ho_ex1', 'ho_ex2', 'ho_ex3'].map(k => `<button type="button" class="bts ho-ex" data-ex="${k}">${esc(t(k))}</button>`).join('')}
      <div class="rangee" style="margin-top:14px"><button type="button" class="bts" data-nav="retour">${esc(t('ho_retour'))}</button><button type="button" class="btp" data-nav="envoyer" disabled>${esc(t('ho_envoyer'))}</button><span class="discret" data-res></span></div>`;
    const z = el.querySelector('#ho-prompt'), err = el.querySelector('#ho-err'), ok = el.querySelector('[data-nav="envoyer"]');
    const maj = () => { C.prompt = z.value; const f = filtrer(z.value); err.textContent = f.length ? t('ho_filtre') : ''; ok.disabled = !z.value.trim() || !!f.length; };
    z.oninput = maj; maj(); try { lierMicros(el); } catch (x) { /* rien */ }
    el.querySelectorAll('[data-ex]').forEach(b => b.onclick = () => { z.value = t(b.dataset.ex); maj(); z.focus(); });
    el.querySelector('[data-nav="retour"]').onclick = () => { Son.clic(); C.mode = null; vue(el); };
    ok.onclick = async () => {
      ok.disabled = true; const res = el.querySelector('[data-res]');
      try { await poster('/api/hote', { action: 'prompt', texte: z.value.trim(), via: 'ecrit' }); Son.clic(); PROP = { statut: 'en_attente', prompt: z.value.trim() }; SIG_P = ''; C.mode = 'attente'; vue(el); }
      catch (x) { res.textContent = x.message; maj(); }
    };
  }
  function vueAttente(el, tete) {
    el.innerHTML = `${tete}<h2>${esc(t('ho_prompt_t'))}</h2><p class="ho-cite">« ${esc((PROP && PROP.prompt) || C.prompt || '')} »</p><p><span class="ho-roue"></span>${esc(t('ho_attente'))}</p><p class="discret">${esc(t('ho_attente_d'))}</p>
      <div class="rangee"><button type="button" class="bts" data-nav="annuler">${esc(t('ho_annuler'))}</button></div>`;
    el.querySelector('[data-nav="annuler"]').onclick = async () => { try { await poster('/api/hote', { action: 'oublier_proposition' }); } catch (x) { /* rien */ } PROP = null; SIG_P = ''; C.mode = 'prompt'; vue(el); };
  }
  function vueApercu(el, tete) {
    if (!PROP || PROP.statut === 'refusee' || !PROP.fiche) {
      el.innerHTML = `${tete}<h2>${esc(t('ho_refusee'))}</h2><p>${esc((PROP && PROP.raison) || '')}</p><div class="rangee"><button type="button" class="btp" data-nav="recommencer">${esc(t('ho_recommencer'))}</button></div>`;
      el.querySelector('[data-nav]').onclick = async () => { try { await poster('/api/hote', { action: 'oublier_proposition' }); } catch (x) { /* rien */ } PROP = null; SIG_P = ''; C.mode = 'prompt'; vue(el); };
      return;
    }
    const f = PROP.fiche, sav = H; H = f; const ex = [choisir(repliques('coin')), choisir(repliques('spontanees')), choisir(repliquesActivite(f.activites[0]))].filter(Boolean); H = sav;
    el.innerHTML = `${tete}<h2>${esc(t('ho_apercu'))} : ${esc(f.nom)}</h2><div class="ho-tete"><canvas width="240" height="240" id="ho-ap"></canvas><div>${recapHTML(f)}</div></div>
      <div class="surtitre" style="margin-top:10px">${esc(t('ho_e_ton'))}</div>${ex.map(s => `<p class="ho-cite">« ${esc(remplir(s, { nom: nomAssistant(), tache: '…', titre: '…' }))} »</p>`).join('')}
      ${(PROP.avertissements || []).length ? `<p class="discret">${esc(t('ho_avert'))} : ${esc(PROP.avertissements.join(' ; '))}</p>` : ''}
      <div class="rangee" style="margin-top:14px"><button type="button" class="btp" data-nav="installer">★ ${esc(t('ho_installer'))}</button><button type="button" class="bts" data-nav="retoucher">${esc(t('ho_retoucher'))}</button><button type="button" class="bts" data-nav="recommencer">${esc(t('ho_recommencer'))}</button><span class="discret" data-res></span></div>`;
    portrait(el.querySelector('#ho-ap'), lookDeFiche(f));
    el.querySelector('[data-nav="installer"]').onclick = async e => { e.target.disabled = true; try { await poster('/api/hote', { action: 'creer', fiche: f }); SIG_H = ''; SIG_P = ''; Panneau.fermer(); setTimeout(charger, 200); } catch (x) { el.querySelector('[data-res]').textContent = x.message; e.target.disabled = false; } };
    el.querySelector('[data-nav="retoucher"]').onclick = () => { Son.clic(); C.ch = choixDepuis(f); C.mode = 'choix'; C.etape = 0; vue(el); };
    el.querySelector('[data-nav="recommencer"]').onclick = async () => { try { await poster('/api/hote', { action: 'oublier_proposition' }); } catch (x) { /* rien */ } PROP = null; SIG_P = ''; C.mode = 'prompt'; vue(el); };
  }
  function propositionChangee(avant, apres) {
    if (!apres || apres.statut !== 'prete' && apres.statut !== 'refusee') return;
    if (avant && avant.statut === apres.statut && JSON.stringify(avant.fiche) === JSON.stringify(apres.fiche)) return;
    if (Panneau.ouvert() === 'hote' && (C.mode === 'attente' || C.mode === 'apercu')) { C.mode = 'apercu'; rendre(); return; }
    if (apres.statut === 'prete') { toast(`<b>${esc(apres.fiche.nom)}</b><br>${esc(t('ho_pret_toast'))}`, { duree: 15000, action: { libelle: t('ho_apercu'), f: () => { C.mode = 'apercu'; rendre(); } } }); try { Son.clic(); } catch (e) { /* rien */ } }
  }

  // ------------------------------------------------------------------ fiche de l'hôte (clic sur lui ou son étiquette)
  function ouvrirFiche() {
    if (!H) return;
    Panneau.remplacer('hote-fiche', el => {
      el.innerHTML = `<div class="surtitre">${esc(t('ho_fiche_sur'))}</div><h2>${esc(H.nom)}</h2><div class="ho-tete"><canvas width="240" height="240" id="ho-fi"></canvas><div><p><b>${esc(t('ho_maintenant'))}</b> : ${esc(texteActivite())}</p>${recapHTML(H)}</div></div>
        <div class="rangee" style="margin-top:12px"><button type="button" class="btp" data-a="parler">${esc(t('ho_faire_parler'))}</button><button type="button" class="bts" data-a="modifier">${esc(t('ho_modifier'))}</button><button type="button" class="bts" data-a="reglages">${esc(t('reglages'))}</button></div>`;
      portrait(el.querySelector('#ho-fi'), lookDeFiche(H));
      el.querySelector('[data-a="parler"]').onclick = () => { Panneau.fermer(); setTimeout(() => dire(choisir(repliques('spontanees')), 6, true), 450); };
      el.querySelector('[data-a="modifier"]').onclick = () => { Panneau.fermer(); setTimeout(() => creer(H), 430); };
      el.querySelector('[data-a="reglages"]').onclick = () => { Panneau.fermer(); setTimeout(() => ouvrirReglages(), 430); };
    });
  }

  // ------------------------------------------------------------------ Réglages : section « Hôte du studio »
  function questeHote() { try { const D = window.Quetes && Quetes.etat(); return D && D.qe && D.qe.quetes && D.qe.quetes['Q-SU-04']; } catch (e) { return null; } }
  function reglages(zone) {
    if (!zone) return;
    const q = questeHote(), ouverte = !q || ['proposee', 'acceptee', 'plus_tard', 'remplie', 'deja_faite'].includes(q.statut) || (REGLAGES && REGLAGES.quetes_actives === false);
    const h = present();
    if (!h) { zone.innerHTML = `<h3 class="rg-groupe">${esc(t('ho_reglages'))}</h3>${ouverte && CAT ? `<div class="rangee"><button type="button" class="bts" id="ho-creer">${esc(t('ho_creer'))}</button></div>` : `<p class="discret">${esc(t('ho_pas_encore'))}</p>`}`;
      const b = zone.querySelector('#ho-creer'); if (b) b.onclick = () => { Panneau.fermer(); setTimeout(() => creer(), 430); }; return; }
    const r = h.reglages || {}, parole = r.parole || 'normal';
    zone.innerHTML = `<h3 class="rg-groupe">${esc(t('ho_reglages'))}</h3><div class="ho-rg"><canvas width="104" height="104" id="ho-rg-p"></canvas><b>${esc(h.nom)}</b><span class="discret">· ${esc(L((parId('tons', h.ton) || {}).nom))}</span></div>
      <label class="reglage"><input type="checkbox" id="ho-sons"${r.sons === false ? '' : ' checked'}> ${esc(t('ho_sons'))}</label>
      <label class="reglage">${esc(t('ho_parole'))} <select id="ho-parole">${['souvent', 'normal', 'rarement', 'jamais'].map(v => `<option value="${v}"${v === parole ? ' selected' : ''}>${esc(t('ho_p_' + v))}</option>`).join('')}</select></label>
      <div class="rangee"><button type="button" class="bts" id="ho-modifier">${esc(t('ho_modifier'))}</button><button type="button" class="bts ho-supprimer" id="ho-supprimer">${esc(t('ho_supprimer'))}</button><span class="discret" id="ho-rg-res"></span></div>`;
    portrait(zone.querySelector('#ho-rg-p'), lookDeFiche(h));
    const res = zone.querySelector('#ho-rg-res');
    const regler = async corps => { try { const x = await poster('/api/hote', Object.assign({ action: 'regler' }, corps)); if (x.hote) { H = x.hote; SIG_H = JSON.stringify(x.hote); } } catch (e) { res.textContent = e.message; } };
    zone.querySelector('#ho-sons').onchange = e => regler({ sons: e.target.checked });
    zone.querySelector('#ho-parole').onchange = e => regler({ parole: e.target.value });
    zone.querySelector('#ho-modifier').onclick = () => { Panneau.fermer(); setTimeout(() => { const x = present(); if (x) creer(x); else reglages(zone); }, 430); };
    const sup = zone.querySelector('#ho-supprimer'); let arme = 0;
    sup.onclick = async () => {
      if (!sup.classList.contains('confirme')) { sup.classList.add('confirme'); sup.textContent = t('ho_confirmer'); clearTimeout(arme); arme = setTimeout(() => { sup.classList.remove('confirme'); sup.textContent = t('ho_supprimer'); }, 5000); return; }
      sup.disabled = true; const nom = h.nom;
      try { await poster('/api/hote', { action: 'supprimer' }); const avant = present(); H = null; SIG_H = 'null'; changement(avant, null); toast(esc(tf('ho_parti', { n: nom })), { duree: 6000 }); reglages(zone); }
      catch (e) { res.textContent = e.message; sup.disabled = false; }
    };
  }

  // ------------------------------------------------------------------ interface publique et essais
  window.HoteStudio = {
    objets, reglages, creer: f => creer(f), ouvrirFiche,
    etiquette: () => H && !(P.x === null) ? { nom: H.nom, p: null, ia: { mode: 'continu', etat: 'continu', picto: 'disponible', texte: texteActivite(), duree: null } } : null,
  };
  if (/[?&]essai\b/.test(location.search) || navigator.webdriver) window.__hoteEssai = {
    etat: () => ({ hote: H, prop: PROP, activite: ACT && ACT.type, texte: texteActivite(), pos: P.x === null ? null : [+P.x.toFixed(2), +P.y.toFixed(2)], marche: P.marche, depart: !!P.depart, cat: !!CAT, mode: C.mode, etape: C.etape }),
    forcer: (type, data) => { if (!H) return null; nouvelle(type, data); ACT.fin = Date.now() + 60000; return ACT.type; },
    teleporter: () => { const q = P.cible; if (q) { P.x = q.x; P.y = q.y; } return true; },
    ecran: () => { const c = Bureau.cam(); return P.monde && P.x !== null ? [P.monde[0] * c.z + c.tx, P.monde[1] * c.z + c.ty] : null; },
    filtre: s => filtrer(s), remplir: (s, d) => remplir(s, jetonsPropres(d)), charger: () => charger(), dire: (s, f) => dire(s, 6, f), choix: () => JSON.parse(JSON.stringify(C.ch))
  };
})();
