/* studio/roadmap.js : panneau « Roadmap » du studio (jalons, tâches, succès, niveau).
 * Lit roadmap.json (format : references/studio.md, « roadmap.json »), sans dépendance.
 * Dans la page : <link rel="stylesheet" href="roadmap.css"> <script src="roadmap.js"></script>
 *   Roadmap.installer({ langue: 'fr', barre: document.querySelector('.outils'), succes: fonctionDuStudio });
 *   Roadmap.voici();   // fin du questionnaire : « Voici ta roadmap » (attend roadmap.json)
 * Studio panel "Roadmap": milestones, tasks, achievements and studio level, read from roadmap.json.
 */
(function (racine) {
  'use strict';

  const STATUTS = ['a_faire', 'en_cours', 'pret', 'verse', 'ecart'];
  const SONS = ['petit', 'moyen', 'grand'];

  // ------------------------------------------------------------ calculs (purs, testables avec node)
  // Avancement d'un ensemble de tâches, pondéré par l'effort (estimation_h, sinon 1) :
  // versé et écart 100 %, prêt 70 %, en cours 35 %, à faire 0 %. Segments en % de l'effort total.
  const POIDS_AV = { verse: 1, ecart: 1, pret: 0.7, en_cours: 0.35, a_faire: 0 };
  const ORDRE_SEG = ['verse', 'pret', 'en_cours', 'ecart', 'a_faire'];
  function avancement(taches) {
    const seg = { verse: 0, pret: 0, en_cours: 0, ecart: 0, a_faire: 0 }; let tot = 0, av = 0, valides = 0, n = 0, resteN = 0, resteH = 0, sansEstim = 0;
    for (const t of (taches || [])) {
      if (!t) continue; n++;
      const st = Object.prototype.hasOwnProperty.call(seg, t.statut) ? t.statut : 'a_faire';
      const h = Number(t.estimation_h) > 0 ? Number(t.estimation_h) : 0, w = h || 1;
      seg[st] += w; tot += w; av += w * POIDS_AV[st];
      if (st === 'verse' || st === 'ecart') valides++; else { resteN++; if (h) resteH += h; else sansEstim++; }
    }
    const pc = {}; for (const k of ORDRE_SEG) pc[k] = tot ? 100 * seg[k] / tot : 0;
    return { seg: pc, avance: tot ? Math.round(100 * av / tot) : 0, valides, total: n, reste_n: resteN, reste_j: Math.round(resteH / 8 * 10) / 10, sans_estimation: sansEstim };
  }
  const LIB_SEG = { fr: { verse: 'versé', pret: 'prêt', en_cours: 'en cours', ecart: 'écart', a_faire: 'à faire', avance: 'avancé', valide: 'validé', reste: 'reste', taches: 'tâches', tache: 'tâche', sans: 'sans estimation', j: 'j' },
                    en: { verse: 'shipped', pret: 'ready', en_cours: 'in progress', ecart: 'waived', a_faire: 'to do', avance: 'progress', valide: 'validated', reste: 'left', taches: 'tasks', tache: 'task', sans: 'not estimated', j: 'd' } };

  function tacheFinie(t) { return !!t && (t.statut === 'verse' || t.statut === 'ecart'); }
  function nombre(v, d) { const n = Number(v); return Number.isFinite(n) && n >= 0 ? n : d; }
  function niveauDepuisXp(xp) { return Math.floor(Math.pow(Math.max(0, xp) / 100, 0.55)) + 1; }
  function seuilNiveau(n) { return Math.ceil(100 * Math.pow(Math.max(0, n - 1), 1 / 0.55) - 1e-6); }

  function calculer(rm) {
    const jal = (rm && Array.isArray(rm.jalons)) ? rm.jalons : [];
    const reg = (rm && rm.niveau) || {};
    const xpT = nombre(reg.xp_par_tache, 100), xpJ = nombre(reg.xp_par_jalon, 500);
    let faites = 0, total = 0, heures = 0, heuresFaites = 0, fermes = 0, enCours = null;
    const jalons = jal.map(j => {
      const taches = Array.isArray(j.taches) ? j.taches : [];
      const f = taches.filter(tacheFinie).length;
      const h = taches.reduce((s, t) => s + nombre(t.estimation_h, 0), 0);
      const hf = taches.filter(tacheFinie).reduce((s, t) => s + nombre(t.estimation_h, 0), 0);
      const ferme = taches.length > 0 && f === taches.length;
      faites += f; total += taches.length; heures += h; heuresFaites += hf; if (ferme) fermes++;
      const r = Object.assign({}, j, { taches, faites: f, total: taches.length, heures: h, heures_faites: hf, ferme, av: avancement(taches),
        pct: taches.length ? Math.round(100 * f / taches.length) : 0 });
      if (!ferme && !enCours) enCours = r;
      return r;
    });
    const xp = faites * xpT + fermes * xpJ;
    const niveau = niveauDepuisXp(xp);
    const rangs = Array.isArray(reg.rangs) ? reg.rangs.slice().sort((a, b) => a.niveau - b.niveau) : [];
    const rang = (rangs.filter(r => niveau >= r.niveau).pop() || {}).nom || '';
    return {
      jalons, faites, total, fermes, heures, heures_faites: heuresFaites,
      pct: total ? Math.round(100 * faites / total) : 0, av: avancement(jal.flatMap(j => (j && Array.isArray(j.taches)) ? j.taches : [])),
      en_cours: enCours, finie: jalons.length > 0 && fermes === jalons.length,
      xp, niveau, xp_niveau: seuilNiveau(niveau), xp_suivant: seuilNiveau(niveau + 1), rang,
      prochain_rang: rangs.find(r => r.niveau > niveau) || null
    };
  }

  // Succès gagnés : jalons fermés (ou marqués obtenus par Claude) + succès final.
  function succesGagnes(c, rm) {
    const out = [];
    for (const j of c.jalons) {
      if (!j.succes || !j.succes.id) continue;
      if (j.ferme || j.succes.obtenu_le) out.push(Object.assign({ jalon: j.id }, j.succes));
    }
    const fin = rm && rm.succes_final;
    if (fin && fin.id && (c.finie || fin.obtenu_le)) out.push(Object.assign({ final: true }, fin));
    return out;
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { calculer, succesGagnes, niveauDepuisXp, seuilNiveau, tacheFinie, STATUTS };
  }
  if (typeof document === 'undefined') return;

  // ------------------------------------------------------------ page
  const opts = { url: 'roadmap.json', langue: 'fr', periode_s: 10, succes: null, barre: null };
  let T = {}, RM = null, C = null, sig = '', ouvert = false, modeVoici = false, attenteDepuis = 0, minuteur = null;

  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch]);
  const t = k => (T && typeof T[k] === 'string') ? T[k] : k;
  const dp = () => opts.langue === 'fr' ? ' :' : ':';
  const cheminSur = (p, ext) => typeof p === 'string' && p.length < 200 && !p.includes('..') && !/^[a-z]+:|^\/\//i.test(p) && ext.test(p);
  const lire = k => { try { return JSON.parse(localStorage.getItem(k) || 'null'); } catch (e) { return null; } };
  const ecrire = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* stockage indisponible */ } };
  const date = s => { if (!s) return ''; const d = new Date(s); return isNaN(d) ? esc(s) : d.toLocaleDateString(opts.langue, { day: 'numeric', month: 'short' }); };

  function icone(ic) {
    if (cheminSur(ic, /\.svg$|\.png$/i)) return `<img src="${esc(ic)}" alt="">`;
    return esc(String(ic || '★').slice(0, 4));
  }

  // ---- son et bannière de succès (si la page hôte n'en fournit pas)
  let audio = null;
  function bip(f, d, o) {
    try {
      audio = audio || new (window.AudioContext || window.webkitAudioContext)();
      const at = audio.currentTime + ((o && o.at) || 0), osc = audio.createOscillator(), g = audio.createGain();
      osc.type = (o && o.type) || 'sine'; osc.frequency.value = f;
      g.gain.setValueAtTime(0, at); g.gain.linearRampToValueAtTime((o && o.gain) || .04, at + .01); g.gain.exponentialRampToValueAtTime(.0001, at + d);
      osc.connect(g).connect(audio.destination); osc.start(at); osc.stop(at + d + .05);
    } catch (e) { /* audio indisponible */ }
  }
  function jouer(son) {
    if (cheminSur(son, /\.(ogg|mp3|wav)$/i)) { try { const a = new Audio(son); a.volume = .6; a.play().catch(() => {}); } catch (e) { /* rien */ } return; }
    const taille = SONS.includes(son) ? son : 'moyen';
    const notes = taille === 'grand' ? [523, 659, 784, 1046, 1318, 1568] : taille === 'moyen' ? [587, 740, 880, 1175] : [659, 880, 1175];
    notes.forEach((f, i) => { bip(f, .22 + (i === notes.length - 1 ? .35 : 0), { type: 'triangle', gain: .05, at: i * .075 }); bip(f * 2, .12, { gain: .012, at: i * .075 + .01 }); });
    if (taille !== 'petit') bip(notes[notes.length - 1] * 1.5, .6, { gain: .02, at: notes.length * .075 });
  }
  const FILE = []; let enCoursSucces = false;
  function banniere(o) { FILE.push(o); if (!enCoursSucces) suivante(); }
  function suivante() {
    const o = FILE.shift(); if (!o) { enCoursSucces = false; return; } enCoursSucces = true;
    let el = document.getElementById('rm-succes');
    if (!el) { el = document.createElement('div'); el.id = 'rm-succes'; el.setAttribute('role', 'status'); el.setAttribute('aria-live', 'polite'); document.body.appendChild(el); }
    el.innerHTML = `<span class="si">${icone(o.icone)}</span><span><span class="sur">${esc(o.taille === 'grand' ? t('grand_succes') : t('succes'))}</span><b>${esc(o.titre)}</b>${o.sous ? `<small>${esc(o.sous)}</small>` : ''}</span>`;
    el.onclick = () => { if (o.clic) o.clic(); };
    requestAnimationFrame(() => el.classList.add('vu'));
    jouer(o.son || o.taille);
    setTimeout(() => { el.classList.remove('vu'); setTimeout(suivante, 500); }, o.taille === 'grand' ? 4200 : 3400);
  }
  function celebrer(o) {
    const taille = SONS.includes(o.son) ? o.son : 'moyen';
    const s = { icone: o.icone, titre: o.titre, sous: o.description || o.sous || '', taille, son: o.son, clic: () => ouvrir() };
    if (typeof opts.succes === 'function') { try { opts.succes(s); if (!SONS.includes(o.son)) jouer(o.son); return; } catch (e) { /* repli */ } }
    banniere(s);
  }

  // ---- détection des nouveaux succès et des montées de niveau
  function nouveautes() {
    const cle = 'studio.roadmap.' + (RM.projet || '') + '.vus';
    const vus = lire(cle), gagnes = succesGagnes(C, RM);
    if (!vus && !modeVoici) { ecrire(cle, { succes: gagnes.map(s => s.id), niveau: C.niveau }); return; } // premier passage hors fin de questionnaire : rien à fêter
    if (!vus) { gagnes.forEach(celebrer); ecrire(cle, { succes: gagnes.map(s => s.id), niveau: C.niveau }); return; }
    const deja = new Set(vus.succes || []);
    for (const s of gagnes) if (!deja.has(s.id)) { deja.add(s.id); celebrer(s); }
    if (vus.niveau && C.niveau > vus.niveau) celebrer({ icone: '▲', titre: `${t('niveau')} ${C.niveau}`, description: C.rang, son: 'grand' });
    ecrire(cle, { succes: [...deja], niveau: Math.max(C.niveau, vus.niveau || 0) });
  }

  // ---- panneau
  function squelette() {
    if (document.getElementById('rm-panneau')) return;
    const p = document.createElement('aside');
    p.id = 'rm-panneau'; p.setAttribute('aria-label', t('titre'));
    p.innerHTML = '<div class="rm-feuille"><button class="rm-fermer" type="button" aria-label="×">×</button><div class="rm-corps"></div></div>';
    document.body.appendChild(p);
    p.querySelector('.rm-fermer').onclick = fermer;
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && ouvert && !(modeVoici && !RM)) fermer(); });
  }

  function ls(k) { const l = (opts && opts.langue) || 'fr'; return (LIB_SEG[l] || LIB_SEG.fr)[k]; }
  function pile(a) { return `<div class="rm-pile" title="${ORDRE_SEG.map(k => ls(k) + ' ' + Math.round(a.seg[k]) + ' %').join(' · ')}">${ORDRE_SEG.map(k => a.seg[k] > 0 ? `<i class="rm-seg-${k}" style="width:${a.seg[k].toFixed(2)}%"></i>` : '').join('')}</div>`; }
  function texteAv(a) { return `${a.avance} % ${ls('avance')} · ${a.valides}/${a.total} ${ls('valide')}${a.reste_n ? ` · ${ls('reste')} : ${a.reste_n} ${a.reste_n > 1 ? ls('taches') : ls('tache')}${a.reste_j ? `, ≈ ${a.reste_j} ${ls('j')}` : ''}${a.sans_estimation ? ` (${a.sans_estimation} ${ls('sans')})` : ''}` : ''}`; }
  // temps restant : estimation de roadmap.json si présente, sinon effort restant pondéré (à faire 100 %, en cours 65 %, prêt 30 %)
  const RESTE_ST = { verse: 0, ecart: 0, pret: 0.3, en_cours: 0.65, a_faire: 1 };
  function baseHeures(taches) { return (taches || []).reduce((s, t) => s + ((Number(t && t.estimation_h) > 0 ? Number(t.estimation_h) : 8) * (RESTE_ST[t && t.statut] ?? 1)), 0); }
  function duree(hh) { const x = +hh || 0; const u = (opts && opts.langue) === 'en' ? ['min', 'h', 'd'] : ['min', 'h', 'j']; if (x <= 0) return '0 ' + u[0]; if (x < 1) return Math.max(5, Math.round(x * 60 / 5) * 5) + ' ' + u[0]; if (x < 8) return Math.round(x * 2) / 2 + ' ' + u[1]; return Math.round(x / 8 * 2) / 2 + ' ' + u[2]; }
  function temps(e, taches) { const est = e || { reste_h: baseHeures(taches), estime: true }; return `≈ ${duree(est.reste_h)}${est.estime ? ((opts && opts.langue) === 'en' ? ' (estimated)' : ' (estimé)') : ''}`; }
  function legende() { return `<div class="rm-legende">${ORDRE_SEG.map(k => `<span><i class="rm-seg-${k}"></i>${esc(ls(k))}</span>`).join('')}</div>`; }
  function barre(pct, texte) { return `<div class="rm-xp"><i style="width:${Math.max(0, Math.min(100, pct)).toFixed(1)}%"></i><span>${esc(texte)}</span></div>`; }

  function vTache(tc) {
    const st = STATUTS.includes(tc.statut) ? tc.statut : 'a_faire', ok = tacheFinie(tc);
    const meta = [tc.poste ? esc(tc.poste) : '', tc.estimation_h ? `${esc(tc.estimation_h)} ${esc(t('heures'))}` : '',
      (tc.depend_de || []).length ? `${esc(t('depend_de'))} ${tc.depend_de.map(esc).join(', ')}` : ''].filter(Boolean).join(' · ');
    return `<li class="rm-tache st-${st}"><span class="rm-case" aria-hidden="true">${ok ? '✓' : st === 'en_cours' ? '…' : ''}</span>
      <span class="rm-tt"><b><span class="rm-id">${esc(tc.id)}</span> ${esc(tc.titre)}</b>${tc.critere ? `<small>${esc(tc.critere)}</small>` : ''}${meta ? `<small class="rm-meta">${meta}</small>` : ''}</span>
      <span class="rm-st">${esc(t('statut_' + st))}</span></li>`;
  }

  function vJalon(j) {
    const s = j.succes, gagne = s && (j.ferme || s.obtenu_le), courant = C.en_cours && C.en_cours.id === j.id;
    return `<section class="rm-jalon${j.ferme ? ' ferme' : ''}${courant ? ' courant' : ''}">
      <h3><span class="rm-jid">${esc(j.id)}</span> ${esc(j.titre)}${j.ferme ? ` <span class="rm-ok">${esc(t('jalon_termine'))}</span>` : courant ? ` <span class="rm-cours">${esc(t('en_cours'))}</span>` : ''}</h3>
      ${j.but ? `<p class="rm-but">${esc(j.but)}</p>` : ''}
      ${pile(j.av)}<p class="rm-discret">${esc(texteAv(j.av))} · <span class="rm-est" title="${esc(j.estimation && j.estimation.fin ? j.estimation.fin.replace('T', ' ') : '')}">${esc(temps(j.estimation, j.taches))}</span></p>
      <p class="rm-discret">${j.critere_fin ? `<b>${esc(t('critere_fin'))}${dp()}</b> ${esc(j.critere_fin)}` : ''}${j.fin_visee ? ` · ${esc(t('fin_visee'))} ${date(j.fin_visee)}` : ''}${j.heures ? ` · ${esc(t('estimation'))} ${Math.round(j.heures)} ${esc(t('heures'))}` : ''}${(j.depend_de || []).length ? ` · ${esc(t('depend_de'))} ${j.depend_de.map(esc).join(', ')}` : ''}</p>
      ${s ? `<div class="rm-badge${gagne ? ' ok' : ''}" title="${esc(s.description || '')}"><span class="bi">${gagne ? icone(s.icone) : '🔒'}</span><span><b>${esc(s.titre)}</b><small>${gagne ? (s.obtenu_le ? `${esc(t('succes_gagne'))} ${date(s.obtenu_le)}` : esc(s.description || '')) : esc(t('succes_verrouille')) + (s.description ? ' · ' + esc(s.description) : '')}</small></span></div>` : ''}
      <ul class="rm-taches">${j.taches.map(vTache).join('')}</ul></section>`;
  }

  function rendre() {
    const corps = document.querySelector('#rm-panneau .rm-corps'); if (!corps) return;
    const btFermer = document.querySelector('#rm-panneau .rm-fermer');
    if (btFermer) btFermer.hidden = modeVoici && !RM;
    if (!RM) {
      const long = attenteDepuis && Date.now() - attenteDepuis > 90000, bloque = modeVoici && attenteDepuis && Date.now() - attenteDepuis > 300000;
      corps.innerHTML = `<div class="rm-surtitre">${esc(t('surtitre'))}</div><h2>${esc(modeVoici ? t('voici') : t('titre'))}</h2>
        <p class="rm-attente"><span class="rm-plume" aria-hidden="true"></span>${esc(modeVoici ? t(long ? 'attente_longue' : 'attente') : t('aucune'))}</p>
        ${bloque ? `<p class="rm-voici">${esc(t('attente_bloquee'))}</p>${typeof opts.relancer === 'function' ? `<button type="button" class="rm-go" data-rm-relancer>${esc(t('relancer'))}</button><p class="rm-voici" data-rm-relance-res></p>` : ''}` : ''}`;
      const bt = corps.querySelector('[data-rm-relancer]');
      if (bt) bt.onclick = () => { bt.disabled = true; Promise.resolve(opts.relancer(t('relance_texte'))).then(() => { corps.querySelector('[data-rm-relance-res]').textContent = t('relance_ok'); }).catch(() => { bt.disabled = false; }); };
      return;
    }
    const gagnes = succesGagnes(C, RM), tous = C.jalons.filter(j => j.succes).length + (RM.succes_final ? 1 : 0);
    const pcXp = 100 * (C.xp - C.xp_niveau) / Math.max(1, C.xp_suivant - C.xp_niveau);
    corps.innerHTML = `<div class="rm-surtitre">${esc(RM.projet || t('surtitre'))}</div>
      <h2>${esc(modeVoici ? t('voici') : t('titre'))}</h2>
      ${modeVoici ? `<p class="rm-voici">${esc(t('voici_aide'))}</p>` : ''}
      <div class="rm-tete"><div class="rm-embleme"><span>niv.</span><b>${C.niveau}</b></div><div style="flex:1;min-width:0">
        <div class="rm-rang">${esc(C.rang || t('niveau'))}</div>
        ${barre(pcXp, `${C.xp - C.xp_niveau} / ${C.xp_suivant - C.xp_niveau} ${t('xp_vers')} ${C.niveau + 1}`)}
        <p class="rm-discret">${esc(t('avancement'))}${dp()} ${C.faites} / ${C.total} ${esc(t('taches'))} (${C.pct} %) · ${C.fermes} / ${C.jalons.length} ${esc(t('jalon').toLowerCase())}s · ★ ${gagnes.length} / ${tous}${C.heures ? ` · ${Math.round(C.heures - C.heures_faites)} ${esc(t('heures'))} ${esc(t('estimation'))}` : ''}</p></div></div>
      ${pile(C.av)}<p class="rm-discret">${esc(texteAv(C.av))} · <span class="rm-est" title="${esc(RM.estimation && RM.estimation.fin ? RM.estimation.fin.replace('T', ' ') : '')}">${esc(temps(RM.estimation, C.jalons.flatMap(j => j.taches)))}</span></p>${legende()}
      <div class="rm-frise" aria-hidden="true">${C.jalons.map(j => `<span class="${j.ferme ? 'ok' : C.en_cours && C.en_cours.id === j.id ? 'cours' : ''}" style="flex:${Math.max(1, j.total)}"><i style="width:${j.av.avance}%"></i><em>${esc(j.id)}</em></span>`).join('')}</div>
      ${C.jalons.map(vJalon).join('')}
      ${RM.succes_final ? `<h3 class="rm-x">${esc(t('succes_titre'))}</h3><div class="rm-badge${C.finie || RM.succes_final.obtenu_le ? ' ok' : ''}"><span class="bi">${C.finie || RM.succes_final.obtenu_le ? icone(RM.succes_final.icone) : '🔒'}</span><span><b>${esc(RM.succes_final.titre)}</b><small>${esc(RM.succes_final.description || '')}</small></span></div>` : ''}
      ${modeVoici ? `<p style="text-align:center;margin-top:22px"><button type="button" class="rm-go">${esc(t('continuer'))}</button></p>` : ''}`;
    const go = corps.querySelector('.rm-go'); if (go) go.onclick = fermer;
  }

  function ouvrir() { squelette(); ouvert = true; rendre(); requestAnimationFrame(() => document.getElementById('rm-panneau').classList.add('ouvert')); }
  function fermer() { ouvert = false; modeVoici = false; const p = document.getElementById('rm-panneau'); if (p) p.classList.remove('ouvert'); }

  // ---- lecture périodique de roadmap.json
  async function charger() {
    try {
      const r = await fetch(opts.url, { cache: 'no-cache' });
      if (!r.ok) throw new Error(r.status);
      const txt = await r.text();
      if (txt === sig) return; sig = txt;
      const rm = JSON.parse(txt);
      if (!rm || !Array.isArray(rm.jalons)) throw new Error('format');
      const premier = !RM; RM = rm; C = calculer(RM);
      majBouton(); nouveautes();
      try { window.dispatchEvent(new CustomEvent('studio:roadmap', { detail: C })); } catch (e) { /* vieux navigateur */ }
      if (ouvert || (premier && modeVoici)) { if (!ouvert) ouvrir(); else rendre(); if (premier && modeVoici) jouer('grand'); }
    } catch (e) { if (ouvert) rendre(); }
  }

  function majBouton() {
    const b = document.getElementById('bt-roadmap'); if (!b) return;
    const p = b.querySelector('.pastille'); if (p) p.textContent = C ? C.pct + ' %' : '';
  }

  function bouton() {
    if (!opts.barre || document.getElementById('bt-roadmap')) return;
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'bt'; b.id = 'bt-roadmap';
    b.innerHTML = `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M2 13.5h3v-4h3v-3h3v-4h3"/><circle cx="3.5" cy="13.5" r=".9"/><path d="M12.5 1.5l1.5 1-1.5 1"/></svg>${esc(t('bouton'))} <span class="pastille rm-pct"></span>`;
    b.onclick = () => (ouvert && !modeVoici ? fermer() : (modeVoici = false, ouvrir()));
    opts.barre.appendChild(b);
  }

  async function textes() {
    for (const lg of [opts.langue, opts.langue === 'fr' ? 'en' : 'fr']) {
      try { const r = await fetch(`questions.${lg}.json`, { cache: 'no-store' }); if (r.ok) { const q = await r.json(); if (q && q.roadmap) { T = q.roadmap; return; } } } catch (e) { /* suivante */ }
    }
  }

  const Roadmap = {
    async installer(o) {
      Object.assign(opts, o || {});
      opts.langue = String(opts.langue || 'fr').slice(0, 2).toLowerCase();
      await textes();
      squelette(); bouton(); await charger();
      clearInterval(minuteur); minuteur = setInterval(charger, Math.max(3, opts.periode_s) * 1000);
      return Roadmap;
    },
    // Fin du questionnaire : non sautable, on attend roadmap.json puis « Voici ta roadmap ».
    voici() { modeVoici = true; attenteDepuis = Date.now(); ouvrir(); if (!RM) setTimeout(function tic() { if (modeVoici && !RM) { rendre(); setTimeout(tic, 15000); } }, 15000); },
    ouvrir, fermer, recharger: charger,
    etat() { return C; },
    calculer, succesGagnes
  };
  racine.Roadmap = Roadmap;
})(typeof window !== 'undefined' ? window : globalThis);
