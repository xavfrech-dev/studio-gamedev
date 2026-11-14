// « Toute l'équipe » : tout le monde au même endroit, même ceux qu'on ne voit pas dans le studio (agents des chaînes Claude,
// fiches d'agent sans bureau, barres de chantier, anciens), et la gestion de chaque poste. Fichier commun aux deux studios
// jumeaux (studio d'origine et skill studio-gamedev) : seuls les branchements (EQ_ENV, défini par la page) changent.
// Données : GET /api/equipe (equipe.py, à partir de l'inventaire du plan de restructuration). Changements par les routes
// existantes : /api/agent (nom, métier), /api/modele (modèle, effort), /api/renvoyer, /api/reembaucher,
// /api/restructuration action « archiver » (barre vers progression/_archives). Rien n'est jamais supprimé.
// EQ_ENV : { langue(), ouvert(), rafraichir(), restruHtml(), restruLier(el), sansEnvoi(), toast(html, erreur), par,
//            renommer(m, nom) -> Promise }
/* global EQ_ENV, esc, poster */
const EQ_TXT = {
  fr: { titre: 'Toute l’équipe', sur: 'Équipe', intro: 'Tout le monde, même ceux qui travaillent hors du studio (chaînes Claude), avec leur état, leur tâche, leur modèle. « Gérer » pour renommer, changer le métier, le modèle, l’effort, renvoyer ou réembaucher.',
    lecture: 'Lecture de l’équipe…', erreur: 'Équipe illisible : ', relancer: 'le serveur du studio est à relancer pour afficher l’équipe (route /api/equipe absente)', tout: 'Tous', travail: 'Au travail', attente: 'En attente', libre: 'Libres', fini: 'Finis',
    personne: 'Personne.', depuis: 'depuis', chaine: 'chaîne', gerer: 'Gérer', fermer_g: 'Fermer', nom: 'Nom', metier: 'Métier (rôle)', modele: 'Modèle', effort: 'Effort',
    enregistrer: 'Enregistrer', renvoyer: 'Renvoyer', confirmer: 'Confirmer le renvoi', apres: 'Au travail : à renvoyer après sa tâche', protege: 'Agent protégé : ne se renvoie pas',
    reembaucher: 'Réembaucher', deja: 'Déjà dans l’équipe', archiver: 'Archiver la barre', archiver_apres: 'Chantier en cours : à archiver après sa fin',
    session: 'Session Claude : se règle dans Claude Code (/model, /effort)', rien_change: 'Rien à changer.', enregistre: 'enregistré ✓', renvoye: 'renvoyé ✓ (fiche gardée dans les anciens)',
    reembauche: 'réembauché ✓', archive: 'archivée ✓ (progression/_archives)', pas_fait: 'Pas fait', motif: 'renvoyé depuis « Toute l’équipe »', plan: 'Remettre de l’ordre',
    maj: 'à jour', eff_: 'par défaut', eff_low: 'bas', eff_medium: 'moyen', eff_high: 'élevé', eff_xhigh: 'très élevé', eff_max: 'max',
    mod_inherit: 'comme la session', mod_haiku: 'Haiku', mod_sonnet: 'Sonnet', mod_opus: 'Opus', mod_fable: 'Fable', col_qui: 'Agent', col_etat: 'État', col_tache: 'Tâche', col_mod: 'Modèle' },
  en: { titre: 'Whole team', sur: 'Team', intro: 'Everyone, even those working outside the studio (Claude chains), with their state, task and model. “Manage” to rename, change the trade, model or effort, let go or hire back.',
    lecture: 'Reading the team…', erreur: 'Team unreadable: ', relancer: 'the studio server needs a restart to show the team (no /api/equipe route)', tout: 'All', travail: 'At work', attente: 'Waiting', libre: 'Free', fini: 'Done',
    personne: 'Nobody.', depuis: 'since', chaine: 'chain', gerer: 'Manage', fermer_g: 'Close', nom: 'Name', metier: 'Trade (role)', modele: 'Model', effort: 'Effort',
    enregistrer: 'Save', renvoyer: 'Let go', confirmer: 'Confirm let go', apres: 'At work: let go after their task', protege: 'Protected agent: cannot be let go',
    reembaucher: 'Hire back', deja: 'Already in the team', archiver: 'Archive the bar', archiver_apres: 'Work in progress: archive it once finished',
    session: 'Claude session: set in Claude Code (/model, /effort)', rien_change: 'Nothing to change.', enregistre: 'saved ✓', renvoye: 'let go ✓ (file kept with former members)',
    reembauche: 'hired back ✓', archive: 'archived ✓ (progression/_archives)', pas_fait: 'Not done', motif: 'let go from “Whole team”', plan: 'Tidy up the team',
    maj: 'up to date', eff_: 'default', eff_low: 'low', eff_medium: 'medium', eff_high: 'high', eff_xhigh: 'very high', eff_max: 'max',
    mod_inherit: 'same as the session', mod_haiku: 'Haiku', mod_sonnet: 'Sonnet', mod_opus: 'Opus', mod_fable: 'Fable', col_qui: 'Agent', col_etat: 'State', col_tache: 'Task', col_mod: 'Model' } };
const EQ = { d: null, t: 0, enCours: false, filtre: 'tout', ouvert: null, res: {}, confirme: null, erreur: '' };
const EQ_MODELES = ['inherit', 'haiku', 'sonnet', 'opus', 'fable'], EQ_EFFORTS = ['', 'low', 'medium', 'high', 'xhigh', 'max'];
const eqT = k => { const l = (typeof EQ_ENV !== 'undefined' && EQ_ENV.langue && EQ_ENV.langue()) || 'fr'; return (EQ_TXT[l] || EQ_TXT.fr)[k] || EQ_TXT.fr[k] || k; };
const eqQuand = s => { s = String(s || ''); if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(s)) return ''; const d = new Date(), auj = new Date(d - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
  return s.slice(0, 10) === auj ? s.slice(11, 16) : s.slice(8, 10) + '/' + s.slice(5, 7) + ' ' + s.slice(11, 16); };
(function eqStyle() {
  if (document.getElementById('eq-style')) return; const st = document.createElement('style'); st.id = 'eq-style';
  st.textContent = `.eq-filtres{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 4px}
.eq-filtres button{border:1px solid rgba(43,36,28,.3);background:transparent;border-radius:999px;padding:6px 13px;font:inherit;font-size:.88em;color:var(--encre);cursor:pointer;min-height:34px}
.eq-filtres button[aria-pressed="true"]{background:var(--encre);color:var(--papier);border-color:var(--encre)}
.eq-filtres button b{font-weight:600;margin-left:4px;opacity:.75}
.eq-groupe{margin-top:14px}.eq-groupe>summary{cursor:pointer;list-style:revert}.eq-groupe h3{display:inline;margin:0}
.eq-groupe h3 small{font-weight:400;color:var(--encre3);font-size:.8em;margin-left:6px}.eq-groupe>p.discret{margin:2px 0 6px}
.eq-tete,.eq-ligne{display:grid;grid-template-columns:minmax(150px,1.25fr) minmax(112px,.75fr) minmax(170px,1.9fr) minmax(104px,.75fr) minmax(86px,auto);gap:4px 12px;align-items:center}
.eq-tete{font:600 11px var(--sans);letter-spacing:.1em;text-transform:uppercase;color:var(--encre2);padding:6px 6px;border-bottom:1px solid rgba(92,79,63,.3)}
.eq-ligne{padding:8px 6px;border-bottom:1px dotted rgba(92,79,63,.3)}.eq-ligne.ouvert{background:rgba(201,149,62,.07)}
.eq-ligne b{display:block}.eq-ligne small{display:block;color:var(--encre3);line-height:1.3;overflow-wrap:anywhere}
.eq-qui,.eq-tache{min-width:0}.eq-tache{overflow-wrap:anywhere}
.eq-etat{display:inline-flex;align-items:center;gap:6px;font-size:.92em}.eq-etat i{width:9px;height:9px;border-radius:50%;flex:none;background:#b7aa92}
.eq-etat.travail i{background:var(--sapin)}.eq-etat.attente i{background:var(--ocre)}.eq-etat.fini i{background:var(--bleu)}
.eq-mod{font-size:.92em}.eq-act{text-align:right}
.eq-gerer{grid-column:1/-1;display:flex;flex-wrap:wrap;gap:8px 12px;align-items:flex-end;border-left:3px solid #c9953e;background:rgba(201,149,62,.1);border-radius:0 10px 10px 0;padding:10px 12px;margin-top:6px}
.eq-gerer label{display:flex;flex-direction:column;font-size:.8em;color:var(--encre2);gap:3px}
.eq-gerer input,.eq-gerer select{border:1px solid rgba(92,79,63,.3);background:#fffdf6;border-radius:8px;padding:5px 7px;color:var(--encre);font:inherit;font-size:1.05em;min-width:9em}
.eq-gerer input[data-eq-role]{min-width:16em}.eq-note{font-size:.88em;color:var(--encre2);font-style:italic}
.eq-plan{margin-top:16px}
@media (max-width:760px){.eq-tete{display:none}.eq-ligne{grid-template-columns:1fr;gap:3px}.eq-act{text-align:left}
.eq-gerer input,.eq-gerer select,.eq-filtres button,.eq-ligne .petit{min-height:44px;font-size:16px}.eq-gerer label,.eq-gerer input,.eq-gerer select{width:100%}}`;
  document.head.appendChild(st);
})();
async function chargerEquipe(force) {
  if (EQ.enCours || (!force && Date.now() - EQ.t < 8000)) return; EQ.enCours = true;
  try { const r = await fetch('/api/equipe', { cache: 'no-store' }); if (r.status === 404) { EQ.erreur = eqT('relancer'); return; } const j = await r.json(); if (j && j.ok) { EQ.d = j; EQ.t = Date.now(); EQ.erreur = ''; } else EQ.erreur = (j && j.erreur) || String(r.status); }
  catch (e) { EQ.erreur = e.message; } finally { EQ.enCours = false; }
}
function eqMembres() { return ((EQ.d && EQ.d.groupes) || []).flatMap(g => g.membres || []); }
function eqModele(m) { return m ? eqT('mod_' + m) : '—'; }
function eqGerer(m) {
  const a = m.actions || {}, opt = (l, v, lib) => l.map(k => `<option value="${esc(k)}"${k === v ? ' selected' : ''}>${esc(lib(k))}</option>`).join('');
  const champs = (a.renommer ? `<label>${esc(eqT('nom'))}<input data-eq-nom maxlength="40" value="${esc(m.nom)}"></label>` : '')
    + (a.metier ? `<label>${esc(eqT('metier'))}<input data-eq-role maxlength="200" value="${esc(m.role || '')}"></label>` : '')
    + (a.modele ? `<label>${esc(eqT('modele'))}<select data-eq-m>${opt(EQ_MODELES.includes(m.modele) ? EQ_MODELES : EQ_MODELES.concat([m.modele]), m.modele || 'inherit', k => eqT('mod_' + k) === 'mod_' + k ? k : eqT('mod_' + k))}</select></label>`
      + `<label>${esc(eqT('effort'))}<select data-eq-e>${opt(EQ_EFFORTS, m.effort || '', k => eqT('eff_' + k))}</select></label>` : (m.session ? `<span class="eq-note">${esc(eqT('session'))}</span>` : ''));
  const ren = a.renvoyer === true ? `<button type="button" class="bts petit" data-eq-renvoyer>${esc(EQ.confirme === m.id ? eqT('confirmer') : eqT('renvoyer'))}</button>`
    : a.renvoyer === 'apres' ? `<span class="eq-note">${esc(eqT('apres'))}${m.occupe ? ' (' + esc(String(m.occupe).slice(0, 80)) + ')' : ''}</span>` : a.renvoyer === 'protege' ? `<span class="eq-note">${esc(eqT('protege'))}</span>` : '';
  const reemb = a.reembaucher === true ? `<button type="button" class="btp petit" data-eq-reemb>${esc(eqT('reembaucher'))}</button>` : a.reembaucher === 'deja' ? `<span class="eq-note">${esc(eqT('deja'))}</span>` : '';
  const arch = a.archiver === true ? `<button type="button" class="bts petit" data-eq-arch>${esc(eqT('archiver'))}</button>` : a.archiver === 'apres' ? `<span class="eq-note">${esc(eqT('archiver_apres'))}</span>` : '';
  return `<div class="eq-gerer">${champs}${a.renommer || a.metier || a.modele ? `<button type="button" class="btp petit" data-eq-ok>${esc(eqT('enregistrer'))}</button>` : ''}${ren}${reemb}${arch}${m.note ? `<span class="eq-note">${esc(m.note)}</span>` : ''}<span class="discret" data-eq-res aria-live="polite">${esc(EQ.res[m.id] || '')}</span></div>`;
}
function eqLigne(m) {
  const a = m.actions || {}, gerable = Object.keys(a).length || m.session || m.note, ouvert = EQ.ouvert === m.id;
  const sous = [m.depuis ? eqT('depuis') + ' ' + eqQuand(m.depuis) : '', m.chaine ? eqT('chaine') + ' ' + m.chaine : ''].filter(Boolean).join(' · ');
  return `<div class="eq-ligne${ouvert ? ' ouvert' : ''}" data-eq="${esc(m.id)}">
    <div class="eq-qui"><b>${esc(m.nom)}</b><small>${esc([m.metier, m.role && m.role !== m.metier ? String(m.role).slice(0, 90) : ''].filter(Boolean).join(' · ') || '—')}</small></div>
    <div><span class="eq-etat ${esc(m.etat)}"><i></i>${esc(m.etat_lib || eqT(m.etat))}</span>${typeof m.progression === 'number' ? `<small>${esc(String(Math.round(m.progression)))} %</small>` : ''}</div>
    <div class="eq-tache">${esc(String(m.tache || '—').slice(0, 160))}${sous ? `<small>${esc(sous)}</small>` : ''}</div>
    <div class="eq-mod">${m.session ? '<span class="discret">session</span>' : esc(m.modele ? eqModele(m.modele) : '—')}${m.effort ? `<small>${esc(eqT('eff_' + m.effort))}</small>` : ''}</div>
    <div class="eq-act">${gerable ? `<button type="button" class="bts petit" data-eq-gerer aria-expanded="${ouvert}">${esc(ouvert ? eqT('fermer_g') : eqT('gerer'))}</button>` : ''}</div>
    ${ouvert ? eqGerer(m) : ''}</div>`;
}
function vEquipe() {
  if (!EQ.d && !EQ.enCours) chargerEquipe(true).then(() => { if (EQ_ENV.ouvert()) EQ_ENV.rafraichir(); });
  const d = EQ.d, f = EQ.filtre, c = (d && d.compte) || {};
  const filtres = ['tout', 'travail', 'attente', 'libre', 'fini'].map(k => `<button type="button" data-eq-filtre="${k}" aria-pressed="${f === k}">${esc(eqT(k))}${k !== 'tout' && c[k] !== undefined ? `<b>${esc(String(c[k]))}</b>` : k === 'tout' && d ? `<b>${esc(String(d.total))}</b>` : ''}</button>`).join('');
  const tete = `<div class="eq-tete" aria-hidden="true"><span>${esc(eqT('col_qui'))}</span><span>${esc(eqT('col_etat'))}</span><span>${esc(eqT('col_tache'))}</span><span>${esc(eqT('col_mod'))}</span><span></span></div>`;
  const groupes = d ? d.groupes.map(g => {
    const l = (g.membres || []).filter(m => f === 'tout' || m.etat === f); if (f !== 'tout' && !l.length) return '';
    const corps = `<p class="discret">${esc(g.aide || '')}</p>${l.length ? tete + l.map(eqLigne).join('') : `<p class="discret">${esc(eqT('personne'))}</p>`}`;
    const titre = `<h3>${esc(g.titre)}<small>${esc(String(l.length))}</small></h3>`;
    return ['barres', 'anciens'].includes(g.id) && f === 'tout' && !l.some(m => m.id === EQ.ouvert) ? `<details class="eq-groupe" data-eq-g="${esc(g.id)}"><summary>${titre}</summary>${corps}</details>`
      : `<section class="eq-groupe" data-eq-g="${esc(g.id)}">${titre}${corps}</section>`; }).join('') : `<p class="discret">${esc(EQ.erreur ? eqT('erreur') + EQ.erreur : eqT('lecture'))}</p>`;
  return `<div class="surtitre">${esc(eqT('sur'))}</div><h2>${esc(eqT('titre'))}</h2><p>${esc(eqT('intro'))}</p>
    ${d ? `<p><b>${esc(d.resume || '')}</b> <span class="discret">· ${esc(eqT('maj'))} ${esc(eqQuand(d.maj))}</span></p>` : ''}
    <div class="eq-filtres" role="group" aria-label="${esc(eqT('titre'))}">${filtres}</div><div class="eq-liste">${groupes}</div>
    <div class="eq-plan"><h3>${esc(eqT('plan'))}</h3>${EQ_ENV.restruHtml()}</div>`;
}
async function eqEnvoyer(m, ligne) {
  const res = ligne.querySelector('[data-eq-res]'), dire = (x, err) => { EQ.res[m.id] = x; if (res) { res.textContent = x; res.className = err ? 'erreur' : 'discret'; } };
  const nom = ligne.querySelector('[data-eq-nom]'), role = ligne.querySelector('[data-eq-role]'), sm = ligne.querySelector('[data-eq-m]'), se = ligne.querySelector('[data-eq-e]');
  const envois = [];
  if (nom && nom.value.trim() && nom.value.trim() !== m.nom) envois.push(['nom', nom.value.trim()]);
  if (role && role.value.trim() && role.value.trim() !== (m.role || '')) envois.push(['role', role.value.trim().replace(/\s+/g, ' ')]);
  const mod = {}; if (sm && sm.value !== (m.modele || 'inherit')) mod.modele = sm.value; if (se && se.value !== (m.effort || '')) mod.effort = se.value;
  if (Object.keys(mod).length) envois.push(['modele', mod]);
  if (!envois.length) { dire(eqT('rien_change')); return; }
  if (EQ_ENV.sansEnvoi()) { document.documentElement.dataset.dernierEnvoi = JSON.stringify({ id: m.id, envois }); dire(eqT('enregistre')); return; }
  try {
    for (const [k, v] of envois) {
      if (k === 'nom') await EQ_ENV.renommer(m, v);
      else if (k === 'role') await poster('/api/agent', { id: m.id, role: v });
      else await poster('/api/modele', Object.assign({ id: m.id, par: EQ_ENV.par, raison: 'Toute l’équipe' }, v));
    }
    dire(eqT('enregistre')); EQ_ENV.toast(`<b>${esc(nom && nom.value.trim() || m.nom)}</b> : ${esc(eqT('enregistre'))}`);
    await chargerEquipe(true); if (EQ_ENV.ouvert()) EQ_ENV.rafraichir();
  } catch (e) { dire(eqT('pas_fait') + ' : ' + e.message, true); EQ_ENV.toast(`<b>${esc(eqT('pas_fait'))}</b><br>${esc(e.message)}`, true); }
}
async function eqAction(m, ligne, quoi) {
  const res = ligne.querySelector('[data-eq-res]'), dire = (x, err) => { EQ.res[m.id] = x; if (res) { res.textContent = x; res.className = err ? 'erreur' : 'discret'; } };
  if (quoi === 'renvoyer' && EQ.confirme !== m.id) { EQ.confirme = m.id; const b = ligne.querySelector('[data-eq-renvoyer]'); if (b) { b.textContent = eqT('confirmer'); b.className = 'btp petit'; } return; }
  const route = { renvoyer: ['/api/renvoyer', { nom: m.cle, motif: eqT('motif') }, 'renvoye'], reembaucher: ['/api/reembaucher', { nom: m.cle }, 'reembauche'],
    archiver: ['/api/restructuration', { action: 'archiver', fichier: m.fichier }, 'archive'] }[quoi];
  EQ.confirme = null;
  if (EQ_ENV.sansEnvoi()) { document.documentElement.dataset.dernierEnvoi = JSON.stringify({ route: route[0], corps: route[1] }); dire(eqT(route[2])); return; }
  ligne.querySelectorAll('button').forEach(b => { b.disabled = true; });
  try { await poster(route[0], route[1]); EQ.res[m.id] = ''; EQ.ouvert = null; EQ_ENV.toast(`<b>${esc(m.nom)}</b> : ${esc(eqT(route[2]))}`); await chargerEquipe(true); if (EQ_ENV.ouvert()) EQ_ENV.rafraichir(); }
  catch (e) { ligne.querySelectorAll('button').forEach(b => { b.disabled = false; }); dire(eqT('pas_fait') + ' : ' + e.message, true); EQ_ENV.toast(`<b>${esc(eqT('pas_fait'))}</b><br>${esc(e.message)}`, true); }
}
function lierEquipe(el) {
  el.querySelectorAll('[data-eq-filtre]').forEach(b => b.onclick = () => { EQ.filtre = b.dataset.eqFiltre; EQ_ENV.rafraichir(); });
  el.querySelectorAll('.eq-ligne[data-eq]').forEach(ligne => {
    const m = eqMembres().find(x => x.id === ligne.dataset.eq); if (!m) return;
    const g = ligne.querySelector('[data-eq-gerer]'); if (g) g.onclick = () => { EQ.ouvert = EQ.ouvert === m.id ? null : m.id; EQ.confirme = null; EQ_ENV.rafraichir();
      const n = el.ownerDocument.querySelector(`.eq-ligne[data-eq="${CSS.escape(m.id)}"] .eq-gerer input, .eq-ligne[data-eq="${CSS.escape(m.id)}"] .eq-gerer select, .eq-ligne[data-eq="${CSS.escape(m.id)}"] .eq-gerer button`); if (n) n.focus({ preventScroll: true }); };
    const ok = ligne.querySelector('[data-eq-ok]'); if (ok) ok.onclick = () => eqEnvoyer(m, ligne);
    ligne.querySelectorAll('.eq-gerer input').forEach(i => i.onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); eqEnvoyer(m, ligne); } });
    const r = ligne.querySelector('[data-eq-renvoyer]'); if (r) r.onclick = () => eqAction(m, ligne, 'renvoyer');
    const re = ligne.querySelector('[data-eq-reemb]'); if (re) re.onclick = () => eqAction(m, ligne, 'reembaucher');
    const ar = ligne.querySelector('[data-eq-arch]'); if (ar) ar.onclick = () => eqAction(m, ligne, 'archiver');
  });
  try { EQ_ENV.restruLier(el); } catch (e) { /* rien */ }
}
// rafraîchi toutes les 15 s, jamais pendant une saisie ni avec un poste ouvert en gestion
setInterval(() => { if (typeof EQ_ENV === 'undefined' || !EQ_ENV.ouvert() || document.hidden || EQ.ouvert) return;
  chargerEquipe().then(() => { const a = document.activeElement; if (EQ_ENV.ouvert() && !EQ.ouvert && !(a && /^(INPUT|SELECT|TEXTAREA)$/.test(a.tagName))) EQ_ENV.rafraichir(); }); }, 15000);
window.__equipe = { EQ, charger: chargerEquipe, membres: eqMembres };   // essais
