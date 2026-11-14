// studio/quetes_page.js : les quêtes du studio dans la page (paquet S4).
// Chargé après le script principal de studio.html : il en réutilise les outils ($, esc, t, Panneau, Succes, Notifs,
// toast, Son, poster, lire, ETAT, CONF, LANGUE…). Il lit trois fichiers écrits par quetes.py : quetes_etat.json,
// habillage.json et table_projet.json, plus le catalogue quetes.json du skill. Il ne lance jamais rien : accepter une
// quête prépare des recrues (lancer: false) et une demande que l'assistant montre avant d'agir.
// Trois parties : le Journal des quêtes (barre du haut, carte, bulle « ! », ligne suivie, boutons des agents de soutien),
// l'habillage (la DA du jeu habille la page par paliers) et la table du bureau (maquette du projet, TableProjet).
'use strict';
(() => {
  if (typeof Panneau === 'undefined' || typeof TXT === 'undefined') return;   // page trop ancienne : rien
  const STYLE_ATELIER = /[?&]style=atelier\b/.test(location.search);

  // ------------------------------------------------------------------ textes (fr = en, mêmes clés)
  Object.assign(TXT.fr, {
    quetes: 'Quêtes', a_quetes: 'Journal des quêtes : ce que le studio te propose pour finir le jeu, et ce que ça rapporte',
    q_titre: 'Journal des quêtes', q_proposee: 'Nouvelle quête', q_proposees: 'Proposées', q_en_cours: 'En cours', q_remplies: 'Remplies',
    q_verrou: 'À venir', q_arrive_apres: 'arrive après', q_objectif: 'Objectif', q_preuve: 'Comment on saura que c’est fait',
    q_propose: 'Le studio propose', q_recompense: 'Récompense', q_accepter: 'Accepter', q_plus_tard: 'Plus tard', q_refuser: 'Refuser',
    q_embaucher: 'Embaucher {n}', q_confier: 'Confier à {n}', q_bureaux_pleins: 'bureaux pleins', q_skill_ok: 'installé', q_skill_non: 'à installer',
    q_acceptee: 'Quête acceptée : les recrues sont prêtes, l’assistant te montre leur fiche avant de lancer quoi que ce soit.',
    q_embauche: '{n} est embauché·e (rien n’est lancé seul).', q_xp: '+{n} XP', q_succes: 'succès « {n} »', q_palier: 'habillage : {n}',
    q_bouton: 'débloque le bouton « {n} »', q_suivre: 'Suivre', q_suivie: 'suivie', q_rattrapage: 'rattrapage', q_principale: 'principale',
    q_secondaire: 'secondaire', q_soutien: 'agent de soutien', q_vide: 'Rien à proposer pour l’instant : le studio te fera signe au bon moment.',
    q_prochaine: 'Prochaine proposition possible vers {h}.', q_tous_actes: 'Tous les actes', q_remplie_le: 'remplie le {d}', q_preuve_ok: 'preuve : {p}',
    q_deja: 'Ton projet remplit déjà {n} quête(s)', q_acte_fini: 'Acte terminé : {n}', q_peinture: 'Coup de peinture : {n}',
    q_maquette: 'Ton studio est en maquette grise : il prendra les couleurs de ton jeu au fil des quêtes.', q_voir_atelier: 'Voir l’Atelier',
    q_revenir_gris: 'Revenir au progressif', q_habillage: 'Habillage du studio', q_palier_n: 'palier {n} sur 5', q_mode: 'Mode',
    q_mode_progressif: 'progressif (suit les quêtes)', q_mode_atelier: 'Atelier (style de référence)', q_mode_jeu: 'jeu (la DA dès qu’elle est validée)',
    q_soutien_t: 'Agents de soutien', q_actif: 'actif', q_reglages: 'Réglages des quêtes', q_actives: 'quêtes proposées', q_secondaires: 'quêtes secondaires',
    q_table: 'Maquette du projet', q_table_d: 'détail {d}/5', q_audit_envoye: 'Demande d’audit envoyée à {n}.', q_audit_txt: 'Fais un audit impartial du projet, des versions et du studio ; liste les corrections à faire, sans rien lancer seul.',
    q_modeles_txt: 'Vérifie le modèle de chaque agent selon sa tâche et propose les changements, sans rien appliquer seul.',
    q_bulle: 'Une quête t’attend', xp_passer: 'Clic pour passer', xp_niveau: 'Niveau {n}', xp_monte: 'Le studio monte d’un niveau', xp_rang: 'rang : {r}', xp_reglage: 'Gains d’XP', xp_complet: 'en grand (milieu de l’écran)', xp_discret: 'discrets (près de la barre)', xp_coupe: 'coupés', q_voir_maquette: 'Voir la maquette en grand', q_ajust: 'Ajustement', q_atelier_actif: 'Style Atelier affiché (référence).'
  });
  Object.assign(TXT.en, {
    quetes: 'Quests', a_quetes: 'Quest log: what the studio suggests to finish the game, and what it earns you',
    q_titre: 'Quest log', q_proposee: 'New quest', q_proposees: 'Offered', q_en_cours: 'In progress', q_remplies: 'Completed',
    q_verrou: 'Coming up', q_arrive_apres: 'comes after', q_objectif: 'Goal', q_preuve: 'How we will know it is done',
    q_propose: 'The studio suggests', q_recompense: 'Reward', q_accepter: 'Accept', q_plus_tard: 'Later', q_refuser: 'Decline',
    q_embaucher: 'Hire {n}', q_confier: 'Hand to {n}', q_bureaux_pleins: 'desks full', q_skill_ok: 'installed', q_skill_non: 'to install',
    q_acceptee: 'Quest accepted: the recruits are ready, the assistant shows you their sheet before anything starts.',
    q_embauche: '{n} is hired (nothing starts on its own).', q_xp: '+{n} XP', q_succes: 'achievement “{n}”', q_palier: 'look: {n}',
    q_bouton: 'unlocks the “{n}” button', q_suivre: 'Track', q_suivie: 'tracked', q_rattrapage: 'catch-up', q_principale: 'main',
    q_secondaire: 'side', q_soutien: 'support agent', q_vide: 'Nothing to offer right now: the studio will call you at the right time.',
    q_prochaine: 'Next offer possible around {h}.', q_tous_actes: 'All acts', q_remplie_le: 'completed on {d}', q_preuve_ok: 'proof: {p}',
    q_deja: 'Your project already completes {n} quest(s)', q_acte_fini: 'Act complete: {n}', q_peinture: 'Fresh paint: {n}',
    q_maquette: 'Your studio is a grey mock-up: it will take on your game’s colours as you complete quests.', q_voir_atelier: 'See the Workshop look',
    q_revenir_gris: 'Back to progressive', q_habillage: 'Studio look', q_palier_n: 'tier {n} of 5', q_mode: 'Mode',
    q_mode_progressif: 'progressive (follows the quests)', q_mode_atelier: 'Workshop (reference look)', q_mode_jeu: 'game (the art direction once approved)',
    q_soutien_t: 'Support agents', q_actif: 'on', q_reglages: 'Quest settings', q_actives: 'quests offered', q_secondaires: 'side quests',
    q_table: 'Project model', q_table_d: 'detail {d}/5', q_audit_envoye: 'Audit request sent to {n}.', q_audit_txt: 'Run an impartial audit of the project, the builds and the studio; list the fixes to make, without launching anything alone.',
    q_modeles_txt: 'Check each agent’s model against its task and suggest changes, without applying anything alone.',
    q_bulle: 'A quest is waiting', xp_passer: 'Click to skip', xp_niveau: 'Level {n}', xp_monte: 'The studio levels up', xp_rang: 'rank: {r}', xp_reglage: 'XP gains', xp_complet: 'big (middle of the screen)', xp_discret: 'subtle (near the bar)', xp_coupe: 'off', q_voir_maquette: 'See the model up close', q_ajust: 'Adjustment', q_atelier_actif: 'Workshop look shown (reference).'
  });
  const L = o => (o && typeof o === 'object') ? (o[LANGUE] || o.fr || o.en || '') : String(o == null ? '' : o);
  const nouveau = (html) => { const d = document.createElement('div'); d.innerHTML = html.trim(); return d.firstChild; };

  // ------------------------------------------------------------------ données
  const D = { cat: null, qe: null, hab: null, tab: null, sigHab: '', sigBoutons: '' };
  const parId = () => { const m = {}; ((D.cat && D.cat.quetes) || []).forEach(q => { m[q.id] = q; }); return m; };
  let PAR_ID = {};
  const actif = () => !(REGLAGES && REGLAGES.quetes_actives === false) && CONF.mode === 'travail';

  // ------------------------------------------------------------------ styles propres (mêmes jetons et composants que la page)
  document.head.appendChild(nouveau(`<style id="quetes-css">
#bt-quetes .pastille,.bt-soutien .pastille{background:var(--ocre)}
#quete-suivie{display:flex;align-items:center;gap:6px;max-width:260px;margin-top:2px;padding:2px 10px;border:1px dashed var(--bord);border-radius:999px;background:transparent;color:#e8dcc2;font:12px var(--sans);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;cursor:pointer}
#quete-suivie[hidden]{display:none}#quete-suivie b{color:#f1d9a4;font-weight:600}
.qj-actes{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0 4px}.qj-actes button{font-size:12px;padding:4px 10px}.qj-actes button.on{border-color:var(--ocre);box-shadow:inset 0 0 0 1px var(--ocre)}
.qj-barre{height:6px;border-radius:3px;background:rgba(92,79,63,.18);overflow:hidden;margin:4px 0 10px}.qj-barre i{display:block;height:100%;background:linear-gradient(90deg,#c9953e,#e2b866)}
.qj h3{font:600 11px var(--sans);letter-spacing:.12em;text-transform:uppercase;color:var(--encre3);margin:14px 0 6px}
.qj-ligne{display:flex;align-items:center;gap:10px;width:100%;text-align:left;padding:8px 10px;margin:4px 0;border:1px solid rgba(92,79,63,.22);border-radius:10px;background:#fffdf6;color:var(--encre)}
.qj-ligne:hover{border-color:var(--ocre)}.qj-ligne .qi{flex:none;width:26px;height:26px;display:grid;place-items:center;border-radius:50%;background:#f3e3bd;color:#7a5418;font-weight:700}
.qj-ligne.faite .qi{background:#dcebd3;color:#2f6b3f}.qj-ligne.verrou{opacity:.6;border-style:dashed;background:transparent}.qj-ligne small{display:block;color:var(--encre3)}
.qj-ligne .qx{margin-left:auto;font:600 12px var(--sans);color:#8a5b12;white-space:nowrap}
.carte-quete .q-pitch{font-style:italic;color:var(--encre2)}
.carte-quete .q-bloc{margin:10px 0;padding:8px 12px;border-left:3px solid var(--ocre);background:rgba(255,250,235,.6);border-radius:0 8px 8px 0}
.carte-quete .q-agents{display:grid;gap:8px;margin:6px 0}.q-agent{display:flex;gap:10px;align-items:center;padding:8px 10px;border:1px solid rgba(92,79,63,.25);border-radius:10px;background:#fffdf6}
.q-agent .av{flex:none;width:34px;height:34px;border-radius:50%;display:grid;place-items:center;background:#e9dcbc;font:600 14px var(--serif);color:#5c4f3f}
.q-agent .q-ag-t{flex:1;min-width:0}.q-agent .q-ag-t small{display:block;color:var(--encre3)}
.q-skills{display:flex;gap:6px;flex-wrap:wrap}.q-skills span{font:12px var(--sans);padding:2px 8px;border-radius:999px;border:1px solid rgba(92,79,63,.25)}.q-skills span.ok{border-color:#6fae5e;color:#2f6b3f}
.q-recomp{display:flex;gap:8px;flex-wrap:wrap;align-items:center}.q-recomp span{display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:999px;background:#f3e3bd;color:#5a3d10;font:600 12.5px var(--sans)}
.q-recomp img{width:18px;height:18px}
.q-palier-apercu{display:inline-block;width:46px;height:14px;border-radius:3px;vertical-align:middle;border:1px solid rgba(0,0,0,.2)}
#hab-maquette{position:fixed;left:50%;transform:translateX(-50%);z-index:30;max-width:min(720px,calc(100vw - 32px));background:#232528!important;display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:6px 0;padding:6px 12px;border:1px dashed var(--bord);border-radius:4px;color:#d6d8db;font:12.5px var(--sans);background:rgba(255,255,255,.03)}
#hab-maquette[hidden]{display:none}#hab-maquette button{font-size:12px;padding:3px 10px}
#hab-maquette button.bts{background:#3a3d42!important;color:#eef0f2!important;border:1px solid #7b8088!important}
#hab-maquette .x{margin-left:auto;min-width:28px;min-height:28px;background:transparent!important;border:1px solid rgba(214,216,219,.55)!important;border-radius:4px;color:#eef0f2!important;font-size:16px;line-height:1;cursor:pointer}
#hab-maquette .x:hover,#hab-maquette .x:focus-visible{background:#3a3d42!important}
#hab-logo{height:30px;width:auto;max-width:120px;object-fit:contain;margin-right:8px;vertical-align:middle}
#hab-peinture{position:fixed;inset:0;z-index:90;pointer-events:none;background:linear-gradient(90deg,transparent 0%,var(--ocre2) 45%,var(--ocre) 55%,transparent 100%);background-size:300% 100%;opacity:.55;mix-blend-mode:color;animation:habPeinture 1.8s ease-in-out forwards}
@keyframes habPeinture{from{background-position:100% 0}to{background-position:0 0;opacity:0}}
@media (prefers-reduced-motion:reduce){#hab-peinture{display:none}}
body.hab-motif::before{content:"";position:fixed;inset:0;z-index:0;pointer-events:none;background-image:var(--hab-motif);opacity:.06}
html[data-habillage="1"] #bureau{filter:saturate(.16) contrast(.96)}
#xp-fete{position:fixed;inset:0;z-index:95;display:grid;place-items:center;pointer-events:none}
#xp-fete .xf-carte{pointer-events:auto;cursor:pointer;display:grid;justify-items:center;gap:2px;padding:18px 34px 16px;border-radius:18px;border:1px solid var(--ocre2);background:radial-gradient(120% 120% at 50% 0%,rgba(60,46,28,.94),rgba(22,18,13,.92));box-shadow:0 18px 50px rgba(0,0,0,.45),0 0 0 6px rgba(226,184,102,.12);color:#f6e7c4;text-align:center;animation:xfRebond .5s cubic-bezier(.2,1.4,.4,1) both;max-width:calc(100vw - 32px)}
#xp-fete .xf-n{font:700 clamp(40px,11vw,84px)/1 var(--serif);color:#f6d891;text-shadow:0 2px 0 rgba(0,0,0,.35),0 0 24px rgba(226,184,102,.45);font-variant-numeric:tabular-nums}
#xp-fete .xf-xp{font:700 13px var(--sans);letter-spacing:.3em;color:#f1d9a4}
#xp-fete .xf-sur{font:600 12px var(--sans);letter-spacing:.18em;text-transform:uppercase;color:#f1d9a4}
#xp-fete .xf-r{max-width:420px;margin-top:4px;font:13px var(--sans);color:#e9dcc0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#xp-fete.niveau .xf-carte{padding:24px 42px 20px;border-width:2px;box-shadow:0 22px 60px rgba(0,0,0,.5),0 0 0 10px rgba(226,184,102,.16),0 0 80px rgba(226,184,102,.35)}
#xp-fete.niveau .xf-n{font-size:clamp(36px,9vw,64px)}
#xp-fete.sort .xf-carte{transition:opacity .28s,transform .28s;opacity:0;transform:scale(.9)}
#xp-fete.discret{display:block}#xp-fete.discret .xf-carte{position:fixed;left:var(--cx,50%);top:var(--cy,60px);transform:translateX(-50%);padding:6px 14px;border-radius:999px;gap:0;grid-auto-flow:column;align-items:baseline;column-gap:6px;animation:xfMonte .4s ease-out both}
#xp-fete.discret .xf-n{font-size:20px}#xp-fete.discret .xf-r{display:none}
#xp-fete .xf-e{position:absolute;left:50%;top:50%;width:7px;height:7px;margin:-3px;border-radius:50%;background:var(--ocre2);box-shadow:0 0 8px rgba(241,217,164,.8);animation:xfEtincelle .9s ease-out both;pointer-events:none}
#xp-fete .xf-e.b{background:#fff6dc;width:4px;height:4px}
#niveau.xp-pulse{animation:xfPulse 1.2s ease-out}
@keyframes xfRebond{0%{transform:scale(.3);opacity:0}55%{transform:scale(1.12);opacity:1}78%{transform:scale(.96)}100%{transform:scale(1)}}
@keyframes xfMonte{from{opacity:0;margin-top:14px}to{opacity:1;margin-top:0}}
@keyframes xfEtincelle{0%{transform:translate(0,0) scale(1);opacity:1}100%{transform:translate(var(--dx),var(--dy)) scale(.2);opacity:0}}
@keyframes xfPulse{0%{box-shadow:0 0 0 0 rgba(226,184,102,.75)}100%{box-shadow:0 0 0 14px rgba(226,184,102,0)}}
@media (prefers-reduced-motion:reduce){#xp-fete .xf-carte{animation:none}#xp-fete .xf-e{display:none}#niveau.xp-pulse{animation:none}}
@media (max-width:760px){#quete-suivie{max-width:60vw}}
</style>`));

  // ------------------------------------------------------------------ barre du haut : Quêtes, Audit et les autres boutons débloqués
  const ICONE_PARCHEMIN = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M4 2.5h8.5v9.5a2 2 0 0 1-2 2H3.5"/><path d="M4 2.5a1.5 1.5 0 0 0-1.5 1.5v1.5H4M3.5 14a1.5 1.5 0 0 0 1.5-1.5v-10"/><path d="M6.5 5.5h4M6.5 8h4M6.5 10.5h2.5"/></svg>';
  const ICONES_BOUTONS = {
    audit: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><circle cx="7" cy="7" r="4.5"/><path d="M10.4 10.4L14 14M5 7l1.5 1.5L9.2 5.6"/></svg>',
    modeles: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><rect x="2" y="2" width="5" height="5" rx="1"/><rect x="9" y="9" width="5" height="5" rx="1"/><path d="M7 4.5h4.5V9M9 11.5H4.5V7"/></svg>'
  };
  function boutonsHaut() {
    const nav = $('#entete nav.outils'); if (!nav) return;
    let bq = $('#bt-quetes');
    if (!bq) {
      bq = nouveau(`<button type="button" class="bt" id="bt-quetes" data-tt-t="a_quetes" title="">${ICONE_PARCHEMIN}<span data-t="quetes">${esc(t('quetes'))}</span> <span class="pastille" id="nb-quetes"></span></button>`);
      const apres = $('#bt-roadmap') || $('#bt-journal'); if (apres && apres.parentNode) apres.parentNode.insertBefore(bq, apres.nextSibling); else nav.appendChild(bq);
      bq.onclick = () => ouvrirJournal();
      bq.title = t('a_quetes');
    }
    bq.hidden = !actif();
    const prop = proposees().length; $('#nb-quetes').textContent = prop ? String(prop) : '';
    bq.classList.toggle('sonne', !!prop);
    // boutons des agents de soutien : seulement si l'agent est embauché et actif (le moteur l'a déjà vérifié)
    const REG_BOUTON = { audit: 'auditeur', modeles: 'controle_modeles' };   // agents de soutien que la page dessine : leur réglage fait foi tout de suite
    const bl = (D.qe && D.qe.deblocages && Array.isArray(D.qe.deblocages.boutons)) ? D.qe.deblocages.boutons.filter(b => b && /^[a-z0-9_-]{2,30}$/.test(b.id || '') && (!REG_BOUTON[b.id] || REGLAGES[REG_BOUTON[b.id]] === true)) : [];
    { const catB = (D.cat.deblocages && D.cat.deblocages.boutons) || {};   // agent rallumé dans la page : son bouton revient sans attendre le moteur
      ((D.qe.deblocages && Array.isArray(D.qe.deblocages.agents)) ? D.qe.deblocages.agents : []).forEach(a => { if (a && REG_BOUTON[a.bouton] && REGLAGES[REG_BOUTON[a.bouton]] === true && !bl.some(b => b.id === a.bouton)) bl.push(Object.assign({}, catB[a.bouton] || {}, { id: a.bouton })); }); }
    { const bm = $('#bt-modeles'); if (bm) bm.hidden = actif() && REGLAGES.controle_modeles !== true; }   // le contrôleur des modèles arrive par sa quête
    const sig = LANGUE + JSON.stringify(bl.map(b => b.id));
    const enPlace = () => bl.every(x => { const el = $('#bt-' + x.id); return !el || el.classList.contains('bt-soutien') || el.parentNode === bq.parentNode; });   // la page peut réordonner sa barre au démarrage
    if (sig === D.sigBoutons && enPlace()) return; D.sigBoutons = sig;
    document.querySelectorAll('.bt-soutien').forEach(b => { if (!bl.some(x => 'bt-' + x.id === b.id)) b.remove(); });
    document.querySelectorAll('[data-q-deplace]').forEach(b => { if (!bl.some(x => 'bt-' + x.id === b.id)) { delete b.dataset.qDeplace; const m = $('#menu-plus'); if (m) m.appendChild(b); } });   // coupé : retour au menu ⋯
    let ref = $('#bt-quetes');
    for (const b of bl) {
      let el = $('#bt-' + b.id);
      if (el && !el.classList.contains('bt-soutien')) {   // bouton que la page a déjà (Audit, Modèles) : il quitte le menu ⋯ et rejoint la barre du haut
        if (el.parentNode !== ref.parentNode || el.previousElementSibling !== ref) { el.dataset.qDeplace = '1'; ref.parentNode.insertBefore(el, ref.nextSibling); }
        ref = el; continue;
      }
      if (!el) {
        el = nouveau(`<button type="button" class="bt bt-soutien" id="bt-${esc(b.id)}">${ICONES_BOUTONS[b.id] || ICONE_PARCHEMIN}<span></span></button>`);
        ref.parentNode.insertBefore(el, ref.nextSibling);
        el.onclick = () => agirSoutien(b);
      }
      ref = el; el.querySelector('span').textContent = L(b.libelle) || b.id;
      el.title = L(b.infobulle); el.setAttribute('aria-label', L(b.libelle));
    }
  }
  async function agirSoutien(b) {
    const qui = b.agent, p = postes().find(x => x.id === qui) || postes().find(x => (x.role || '').toLowerCase().includes(b.id));
    if (!p) { toast(esc(t('q_bureaux_pleins')), { erreur: true }); return; }
    const txt = b.id === 'audit' ? t('q_audit_txt') : b.id === 'modeles' ? t('q_modeles_txt') : L(b.infobulle);
    try { await posterFond('/api/demande', { cible: p.id, texte: txt, via: 'ecrit' }); toast(esc(tf('q_audit_envoye', { n: nomPoste(p) }))); try { Son.clic && Son.clic(); } catch (e) { /* rien */ } }
    catch (e) { /* toast déjà montré */ }
  }

  // ------------------------------------------------------------------ ligne « quête suivie » sous le niveau
  function ligneSuivie() {
    let el = $('#quete-suivie');
    if (!el) { const niv = $('#niveau'); if (!niv) return; el = nouveau('<button type="button" id="quete-suivie" hidden></button>'); niv.insertAdjacentElement('afterend', el); el.onclick = () => { const id = el.dataset.q; if (id) ouvrirQuete(id); }; }
    const id = D.qe && D.qe.suivie, q = id && PAR_ID[id], e = id && D.qe.quetes && D.qe.quetes[id];
    if (!actif() || !q || !e || ['remplie', 'deja_faite', 'refusee'].includes(e.statut)) { el.hidden = true; return; }
    const crit = (q.fini && (q.fini.tous || q.fini.un_de)) || [], fait = Array.isArray(e.criteres_ok) ? e.criteres_ok.length : null;
    el.hidden = false; el.dataset.q = id;
    el.innerHTML = `⚑ <b>${esc(L(q.titre))}</b>${fait != null && crit.length > 1 ? ` · ${fait}/${crit.length}` : ''}`;
    el.title = L(q.objectif);
  }

  // ------------------------------------------------------------------ listes
  const statut = id => ((D.qe && D.qe.quetes && D.qe.quetes[id]) || {}).statut || 'cachee';
  const proposees = () => ((D.cat && D.cat.quetes) || []).filter(q => (OPT[q.id] || statut(q.id)) === 'proposee');
  const OPT = {};   // réponses envoyées et pas encore relues par le moteur (affichage immédiat)

  function recompenseHTML(q) {
    const r = q.recompense || {}, out = [];
    if (r.xp) out.push(`<span>★ ${esc(tf('q_xp', { n: r.xp }))}</span>`);
    if (r.succes) out.push(`<span>${cheminSur(r.succes.icone, /\.(svg|png)$/i) ? `<img src="${esc(r.succes.icone)}" alt="">` : '🏅'} ${esc(tf('q_succes', { n: L(r.succes.titre) }))}</span>`);
    if (r.habillage) { const n = (Array.isArray(D.cat.habillage) ? D.cat.habillage : []).find(x => x && x.palier === r.habillage) || null;
      out.push(`<span><i class="q-palier-apercu" style="background:linear-gradient(90deg,#8a8f96,${r.habillage >= 2 ? 'var(--ocre)' : '#8a8f96'})"></i> ${esc(tf('q_palier', { n: n ? L(n.nom) : r.habillage + '/5' }))}</span>`); }
    if (r.deblocage && r.deblocage.bouton) { const b = (D.cat.deblocages && D.cat.deblocages.boutons || {})[r.deblocage.bouton]; out.push(`<span>🔓 ${esc(tf('q_bouton', { n: b ? L(b.libelle) : r.deblocage.bouton }))}</span>`); }
    if (r.decor) out.push(`<span>🪴 ${esc(L(r.decor.nom || String(r.decor).replace(/_/g, ' ')))}</span>`);
    return `<div class="q-recomp">${out.join('')}</div>`;
  }
  function agentsHTML(q, e) {
    const props = (e.propositions && e.propositions.agents) || (q.propositions && q.propositions.agents || []).map(a => ({ agent: a.agent, action: 'recruter', mission: a.mission }));
    if (!props.length) return '';
    return `<div class="q-agents">${props.map(a => {
      const f = (D.cat.agents || {})[a.agent] || {}, nom = L(a.nom_affiche || f.nom_affiche) || a.agent, role = L(a.role || f.role);
      const bouton = a.action === 'recruter' || (a.action === 'activer' && !a.deja_actif) ? `<button type="button" class="btp" data-embaucher="${esc(a.agent)}">${esc(tf('q_embaucher', { n: nom }))}</button>`
        : a.action === 'confier' ? `<span class="discret">${esc(tf('q_confier', { n: a.confier_a || nom }))}</span>` : `<span class="discret">${esc(t('q_bureaux_pleins'))}</span>`;
      return `<div class="q-agent"><span class="av">${esc(nom.slice(0, 1).toUpperCase())}</span><span class="q-ag-t"><b>${esc(nom)}</b>${f.soutien ? ` <span class="discret">· ${esc(t('q_soutien'))}</span>` : ''}<small>${esc(role)}</small><small>${esc(L(a.mission))}</small></span>${e.statut === 'proposee' ? bouton : ''}</div>`;
    }).join('')}</div>`;
  }
  function skillsHTML(e, q) {
    const l = (e.propositions && e.propositions.skills) || ((q.propositions && q.propositions.skills) || []).map(n => ({ nom: n, installe: null }));
    return l.length ? `<div class="q-skills">${l.map(s => `<span class="${s.installe ? 'ok' : ''}" title="${esc(s.installe === true ? t('q_skill_ok') : s.installe === false ? t('q_skill_non') : '')}">${esc(s.nom)}${s.installe === true ? ' ✓' : ''}</span>`).join('')}</div>` : '';
  }
  function carteQuete(el, id) {
    const q = PAR_ID[id], e = (D.qe.quetes || {})[id] || {}; if (!q) return;
    const acte = (D.cat.actes || []).find(a => a.id === q.acte), st = OPT[id] || e.statut;
    const props = agentsHTML(q, Object.assign({}, e, { statut: st })) + skillsHTML(e, q);
    const genre = q.soutien ? t('q_soutien') : q.type === 'principale' ? t('q_principale') : t('q_secondaire');
    el.innerHTML = `<div class="carte-dec carte-quete"><div class="surtitre">${esc(L(acte && acte.titre))} · ${esc(genre)}${e.rattrapage ? ' · ' + esc(t('q_rattrapage')) : ''}${D.qe.suivie === id ? ' · ⚑ ' + esc(t('q_suivie')) : ''}</div>
      <h2>${esc(L(q.titre))}</h2><p class="q-pitch">${esc(L(q.pitch))}</p>
      <div class="q-bloc"><b>${esc(t('q_objectif'))}</b><br>${esc(L(q.objectif))}</div>
      <div class="q-bloc"><b>${esc(t('q_preuve'))}</b><br>${esc(L(q.preuve_attendue))}${e.preuve ? `<br><span class="discret">${esc(tf('q_preuve_ok', { p: e.preuve }))}</span>` : ''}</div>
      ${props ? `<div class="surtitre" style="margin-top:12px">${esc(t('q_propose'))}</div>${props}` : ''}
      <div class="surtitre" style="margin-top:12px">${esc(t('q_recompense'))}</div>${recompenseHTML(q)}
      <div class="rangee" style="margin-top:14px">${st === 'proposee' || st === 'plus_tard' ? `<button type="button" class="btp" data-q="accepter">★ ${esc(t('q_accepter'))}</button><button type="button" class="bts" data-q="plus_tard">${esc(t('q_plus_tard'))}</button>${q.type !== 'principale' || e.rattrapage ? `<button type="button" class="bts" data-q="refuser">${esc(t('q_refuser'))}</button>` : ''}`
        : st === 'acceptee' && D.qe.suivie !== id ? `<button type="button" class="bts" data-q="suivre">⚑ ${esc(t('q_suivre'))}</button>` : ''}<span class="discret" data-q-res></span></div></div>`;
    const res = el.querySelector('[data-q-res]');
    const envoyer = async (action, agents) => {
      el.querySelectorAll('button').forEach(b => { b.disabled = true; });
      try {
        const r = await poster('/api/quete', Object.assign({ id, action }, agents ? { agents } : {}));
        if (action === 'accepter' || action === 'plus_tard' || action === 'refuser') OPT[id] = { accepter: 'acceptee', plus_tard: 'plus_tard', refuser: 'refusee' }[action];
        if (action === 'suivre') D.qe.suivie = id;
        const SOUT = { auditeur: 'auditeur', controle_modeles: 'controleur-modeles' };
        (r.actives || []).forEach(k => { REGLAGES = Object.assign({}, REGLAGES, { [k]: true }); });
        try { if ((r.actives || []).length && typeof majAuditeur === 'function') majAuditeur(); } catch (err) { /* rien */ }
        const embauches = (r.embauches || []).map(x => x.nom_affiche || x.nom).concat((r.actives || []).map(k => L(((D.cat.agents || {})[SOUT[k]] || {}).nom_affiche) || k));
        if (action === 'accepter') { toast(`<b>${esc(L(q.titre))}</b><br>${esc(embauches.length ? embauches.map(n => tf('q_embauche', { n })).join(' ') : t('q_acceptee'))}`, { duree: 6000 }); try { Son.succes('petit'); } catch (err) { /* rien */ } }
        majTout(); Panneau.fermer();
        if ((r.embauches && r.embauches.length) || (r.actives && r.actives.length)) setTimeout(() => { try { chargerTout(); } catch (err) { /* rien */ } }, 400);
      } catch (err) { res.textContent = err.message; el.querySelectorAll('button').forEach(b => { b.disabled = false; }); }
    };
    el.querySelectorAll('[data-q]').forEach(b => { b.onclick = () => envoyer(b.dataset.q); });
    el.querySelectorAll('[data-embaucher]').forEach(b => { b.onclick = () => envoyer('accepter', [b.dataset.embaucher]); });
  }
  function ouvrirQuete(id) { if (PAR_ID[id] && D.qe) Panneau.remplacer('quete:' + id, el => carteQuete(el, id)); }
  let FILTRE_ACTE = '';
  function ouvrirJournal() {
    if (!D.cat || !D.qe) return;
    Panneau.remplacer('quetes', el => {
      const actes = D.cat.actes || [], qs = (D.cat.quetes || []).filter(q => !FILTRE_ACTE || q.acte === FILTRE_ACTE);
      const st = q => OPT[q.id] || statut(q.id);
      const grp = { proposee: [], acceptee: [], faite: [], verrou: [] };
      for (const q of qs) { const s = st(q); if (s === 'proposee' || s === 'plus_tard') grp.proposee.push(q); else if (s === 'acceptee') grp.acceptee.push(q); else if (s === 'remplie' || s === 'deja_faite') grp.faite.push(q); else if (s !== 'refusee' && (D.qe.quetes[q.id] || {}).existe !== false) grp.verrou.push(q); }
      const ligne = (q, cls, ic, sous) => `<button type="button" class="qj-ligne ${cls}" data-qid="${esc(q.id)}"><span class="qi">${ic}</span><span><b>${esc(L(q.titre))}</b><small>${esc(sous)}</small></span><span class="qx">${q.recompense && q.recompense.xp ? '+' + q.recompense.xp + ' XP' : ''}</span></button>`;
      const acteDe = q => L((actes.find(a => a.id === q.acte) || {}).titre);
      const total = qs.length, faites = grp.faite.length;
      const hab = D.qe.habillage || {}, palier = hab.palier || 1;
      el.innerHTML = `<div class="qj"><h2>${esc(t('q_titre'))}</h2>
        <div class="qj-actes" role="group"><button type="button" class="bts${FILTRE_ACTE ? '' : ' on'}" data-acte="">${esc(t('q_tous_actes'))}</button>${actes.map(a => `<button type="button" class="bts${FILTRE_ACTE === a.id ? ' on' : ''}" data-acte="${esc(a.id)}">${(D.qe.actes_finis || []).includes(a.id) ? '✓ ' : ''}${esc(L(a.titre))}</button>`).join('')}</div>
        <div class="qj-barre" title="${faites}/${total}"><i style="width:${total ? (100 * faites / total).toFixed(1) : 0}%"></i></div>
        ${grp.proposee.length ? `<h3>${esc(t('q_proposees'))}</h3>` + grp.proposee.map(q => ligne(q, '', '!', acteDe(q) + ' · ' + L(q.pitch))).join('') : `<p class="discret">${esc(t('q_vide'))}${D.qe.prochaine_proposition ? ' ' + esc(tf('q_prochaine', { h: String(D.qe.prochaine_proposition).slice(11, 16) })) : ''}</p>`}
        ${grp.acceptee.length ? `<h3>${esc(t('q_en_cours'))}</h3>` + grp.acceptee.map(q => ligne(q, '', '⚑', L(q.objectif))).join('') : ''}
        ${grp.faite.length ? `<h3>${esc(t('q_remplies'))} · ${faites}</h3>` + grp.faite.map(q => { const e = D.qe.quetes[q.id] || {}; return ligne(q, 'faite', '✓', (e.remplie_le ? tf('q_remplie_le', { d: String(e.remplie_le).slice(0, 10) }) : '') + (e.preuve ? ' · ' + e.preuve : '')); }).join('') : ''}
        ${grp.verrou.length ? `<h3>${esc(t('q_verrou'))}</h3>` + grp.verrou.slice(0, 12).map(q => ligne(q, 'verrou', '·', acteDe(q) + ((q.prerequis || []).length ? ' · ' + t('q_arrive_apres') + ' : ' + q.prerequis.map(p => L((PAR_ID[p] || {}).titre) || p).join(', ') : ''))).join('') : ''}
        <h3>${esc(t('q_habillage'))}</h3>
        <p>${esc(L(hab.nom) || '')} · ${esc(tf('q_palier_n', { n: palier }))}${STYLE_ATELIER ? ' · ' + esc(t('q_atelier_actif')) : ''}</p>
        ${(hab.ajustements || []).slice(0, 3).map(a => `<p class="discret">${esc(t('q_ajust'))} : ${esc(L(a))}</p>`).join('')}
        <div class="rangee"><label class="discret" for="qj-mode">${esc(t('q_mode'))}</label><select id="qj-mode">${['progressif', 'atelier', 'jeu'].map(m => `<option value="${m}"${(hab.mode || 'progressif') === m ? ' selected' : ''}>${esc(t('q_mode_' + m))}</option>`).join('')}</select></div>
        ${soutienHTML()}
        ${D.tab ? `<h3>${esc(t('q_table'))}</h3><p class="discret">${esc(L(D.tab.description))} · ${esc(tf('q_table_d', { d: D.tab.detail }))}</p><div class="rangee"><button type="button" class="bts" id="qj-maquette">${esc(t('q_voir_maquette'))}</button></div>` : ''}
        <h3>${esc(t('q_reglages'))}</h3>
        <div class="rangee"><label class="reglage"><input type="checkbox" id="qj-actives"${REGLAGES.quetes_actives === false ? '' : ' checked'}> ${esc(t('q_actives'))}</label><label class="reglage"><input type="checkbox" id="qj-sec"${REGLAGES.quetes_secondaires === false ? '' : ' checked'}> ${esc(t('q_secondaires'))}</label><span class="discret" data-res></span></div>
        <div class="rangee"><label class="discret" for="qj-xp">${esc(t('xp_reglage'))}</label><select id="qj-xp">${['complet', 'discret', 'coupe'].map(m => `<option value="${m}"${LS.get('xp_fete', 'complet') === m ? ' selected' : ''}>${esc(t('xp_' + m))}</option>`).join('')}</select></div></div>`;
      el.querySelectorAll('[data-acte]').forEach(b => { b.onclick = () => { FILTRE_ACTE = b.dataset.acte; ouvrirJournal(); }; });
      el.querySelectorAll('[data-qid]').forEach(b => { b.onclick = () => { const id = b.dataset.qid; if (statut(id) !== 'cachee' || OPT[id]) ouvrirQuete(id); }; });
      const reg = async corps => { const z = el.querySelector('[data-res]'); try { const r = await poster('/api/reglages', corps); REGLAGES = r.reglages || Object.assign({}, REGLAGES, corps); z.textContent = '✓';
        if (corps.habillage_mode) modeLocal(corps.habillage_mode); else majTout(); try { if (typeof majAuditeur === 'function') majAuditeur(); } catch (e2) { /* rien */ } } catch (err) { z.textContent = err.message; } };
      { const bm = el.querySelector('#qj-maquette'); if (bm) bm.onclick = () => TableProjet.ouvrir(); }
      el.querySelector('#qj-mode').onchange = e => reg({ habillage_mode: e.target.value });
      el.querySelector('#qj-actives').onchange = e => reg({ quetes_actives: e.target.checked });
      el.querySelector('#qj-sec').onchange = e => reg({ quetes_secondaires: e.target.checked });
      el.querySelector('#qj-xp').onchange = e => { LS.set('xp_fete', e.target.value); if (e.target.value !== 'coupe') Xp.essai(10, t('xp_reglage')); };
      el.querySelectorAll('[data-soutien]').forEach(c => { c.onchange = () => reg({ [({ auditeur: 'auditeur', 'controleur-modeles': 'controle_modeles' })[c.dataset.soutien] || ('soutien.' + c.dataset.soutien)]: c.checked }); });
    });
  }
  function soutienHTML() {
    const ags = (D.qe.deblocages && D.qe.deblocages.agents) || []; if (!ags.length) return '';
    return `<h3>${esc(t('q_soutien_t'))}</h3><div class="rangee">${ags.filter(a => a && /^[a-z0-9-]{3,40}$/.test(a.agent || '')).map(a => { const f = (D.cat.agents || {})[a.agent] || {};
      return `<label class="reglage"><input type="checkbox" data-soutien="${esc(a.agent)}"${a.actif === false ? '' : ' checked'}> ${esc(L(f.nom_affiche) || a.agent)} <span class="discret">${a.embauche ? '' : '(—)'}</span></label>`; }).join('')}</div>`;
  }

  // ------------------------------------------------------------------ annonces (proposée, remplie, acte, coup de peinture)
  const CLE_N = 'quetes_annonce_n:' + (location.port || '');
  function annonces() {
    const l = (D.qe && Array.isArray(D.qe.annonces)) ? D.qe.annonces.filter(a => a && Number.isFinite(+a.n)) : [];
    if (!l.length) return;
    const max = Math.max(...l.map(a => +a.n)), vu = +LS.get(CLE_N, -1);
    if (vu < 0 || vu > max) { LS.set(CLE_N, max); return; }        // premier chargement (ou état remis à zéro) : pas de pluie d'annonces
    for (const a of l.filter(a => +a.n > vu).sort((x, y) => x.n - y.n)) {
      try {
        if (a.type === 'quete_proposee' && actif()) {
          const titre = L(a.titre);
          Notifs.ajouter({ id: 'quete-' + a.quete + '-' + a.n, type: 'info', titre: t('q_proposee'), ligne: titre, cible: null }, true);
          toast(`<b>! ${esc(t('q_proposee'))}</b><br>${esc(titre)}`, { duree: 7000, action: { libelle: t('q_titre'), f: () => ouvrirQuete(a.quete) } });
          try { Son.cloche(); } catch (e) { /* rien */ }
          try { Bureau.dire('assistant', titre, 7); } catch (e) { /* rien */ }
        } else if (a.type === 'quete_remplie') {
          const q = PAR_ID[a.quete] || {}; Xp.raison(L(q.titre) || L(a.titre));
          Succes.ajouter({ id: 'quete-' + a.quete, icone: cheminSur(a.icone, /\.(svg|png)$/i) ? a.icone : '★', titre: L(a.titre), sous: `${L(q.titre)} · +${a.xp || 0} XP`, taille: a.son || 'moyen', clic: () => ouvrirJournal() });
        } else if (a.type === 'deja_faites') {
          Xp.raison(L(a.titre) || tf('q_deja', { n: a.n }));
          Succes.ajouter({ id: 'quetes-deja-' + a.n, icone: '✓', titre: L(a.titre) || tf('q_deja', { n: a.n }), sous: '+' + (a.xp || 0) + ' XP', taille: 'moyen', clic: () => ouvrirJournal() });
        } else if (a.type === 'acte_fini') {
          Xp.raison(tf('q_acte_fini', { n: L(a.titre) }));
          Succes.ajouter({ id: 'acte-' + a.acte, icone: cheminSur(a.icone, /\.(svg|png)$/i) ? a.icone : '⚑', titre: tf('q_acte_fini', { n: L(a.titre) }), sous: '+' + (a.xp || 0) + ' XP', taille: 'grand' });
        } else if (a.type === 'coup_de_peinture' && !STYLE_ATELIER) {
          Habillage.peinture();
          Succes.ajouter({ id: 'peinture-' + a.a, icone: '🎨', titre: tf('q_peinture', { n: L(a.titre) }), sous: tf('q_palier_n', { n: a.a }), taille: a.son || 'grand' });
        }
      } catch (e) { erreur('annonce de quête', e); }
    }
    LS.set(CLE_N, max);
  }

  // ------------------------------------------------------------------ habillage : la DA du jeu habille la page, palier par palier
  const Habillage = (() => {
    const ORIG = []; const VUES = new WeakSet(); let applique = '';
    const COUL = /#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b|rgba?\([^)]*\)/g;
    function regles(liste, out) { for (const r of liste) { try { if (r.style && r.selectorText !== undefined) out.push(r); else if (r.cssRules) regles(r.cssRules, out); } catch (e) { /* rien */ } } return out; }
    function relever() {
      for (const s of document.styleSheets) {
        if (VUES.has(s) || (s.ownerNode && s.ownerNode.id === 'hab-polices')) continue;
        let rs; try { rs = s.cssRules; } catch (e) { continue; }      // feuille d'une autre origine : jamais lue
        VUES.add(s);
        for (const r of regles(rs, [])) {
          const st = r.style;
          for (let i = 0; i < st.length; i++) {
            const p = st[i], v = st.getPropertyValue(p); if (!v) continue;
            if (COUL.test(v) || /radius$/.test(p) || p === 'box-shadow' || p === 'font-family' || p === 'text-shadow') ORIG.push({ st, p, v, pr: st.getPropertyPriority(p) });
            COUL.lastIndex = 0;
          }
        }
      }
    }
    const hex2 = h => { h = h.slice(1); if (h.length <= 4) h = h.split('').map(c => c + c).join(''); return [0, 2, 4, 6].map(i => i < h.length ? parseInt(h.slice(i, i + 2), 16) : 255); };
    function lireCouleur(s) {
      if (s[0] === '#') { const [r, g, b, a] = hex2(s); return [r, g, b, a / 255]; }
      const n = s.match(/[\d.]+%?/g) || []; const v = n.map((x, i) => x.endsWith('%') ? (i < 3 ? 2.55 : .01) * parseFloat(x) : parseFloat(x));
      return [v[0] || 0, v[1] || 0, v[2] || 0, v.length > 3 ? v[3] : 1];
    }
    const ecrire = ([r, g, b, a]) => { const c = x => Math.round(clamp(x, 0, 255)); return a >= .999 ? '#' + [r, g, b].map(x => c(x).toString(16).padStart(2, '0')).join('') : `rgba(${c(r)},${c(g)},${c(b)},${+a.toFixed(3)})`; };
    function gris([r, g, b, a]) { const l = .299 * r + .587 * g + .114 * b; const k = .9; return [r + (l + 1 - r) * k, g + (l + 2 - g) * k, b + (l + 5 - b) * k, a]; }
    // Deux familles d'ancres : le texte (encre, texte, accents) et les fonds (nuit, papier, accents). Dans le style Atelier,
    // papier et texte sont presque la même couleur mais n'ont pas le même rôle : la propriété CSS décide.
    const FG = ['--texte', '--encre', '--encre2', '--encre3', '--ocre', '--ocre2', '--sapin', '--rouge', '--bleu', '--alerte'];
    const BG = ['--nuit', '--nuit2', '--papier', '--ocre', '--ocre2', '--sapin', '--rouge', '--bleu', '--alerte'];
    function ancrages(jetons, cles) {
      const A = [];
      for (const o of ORIG) if (cles.includes(o.p) && jetons[o.p] && /^#[0-9a-f]{6}$/i.test(String(jetons[o.p])) && /^#[0-9a-f]{6}$/i.test(o.v.trim())) A.push([lireCouleur(o.v.trim()), lireCouleur(jetons[o.p])]);
      return A;
    }
    const lum = ([r, g, b]) => { const f = x => { x /= 255; return x <= .03928 ? x / 12.92 : Math.pow((x + .055) / 1.055, 2.4); }; return .2126 * f(r) + .7152 * f(g) + .0722 * f(b); };
    const contraste = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + .05) / (Math.min(x, y) + .05); };
    const TEXTE = /^(color|fill|stroke|caret-color|-webkit-text-fill-color|text-decoration-color|outline-color|column-rule-color)$/;
    function versJeu(c, A) {
      let sw = 0; const out = [0, 0, 0];
      const d = A.map(([a]) => Math.hypot(c[0] - a[0], c[1] - a[1], c[2] - a[2])).map((x, i) => [x, i]).sort((x, y) => x[0] - y[0]).slice(0, 3);
      for (const [dist, i] of d) { const w = 1 / (dist * dist + 1); sw += w; const [a, b] = A[i]; for (let k = 0; k < 3; k++) out[k] += w * (b[k] + (c[k] - a[k])); }
      return [out[0] / sw, out[1] / sw, out[2] / sw, c[3]];
    }
    function polices(p, v, palier) {
      if (palier === 1) return 'system-ui,-apple-system,"Segoe UI",Arial,sans-serif';
      if (palier >= 3) { if (/Georgia|serif\b/.test(v) && !/Jeu Texte/.test(v) && !/sans-serif/.test(v.replace(/"[^"]*"/g, ''))) return '"Jeu Texte",' + v; if (/Segoe|system-ui|sans-serif|Arial/.test(v) && !/Jeu Interface/.test(v)) return '"Jeu Interface",' + v; }
      return v;
    }
    function remettre() { for (const o of ORIG) try { o.st.setProperty(o.p, o.v, o.pr); } catch (e) { /* rien */ } }
    function appliquer(hab) {
      relever();
      const palier = STYLE_ATELIER || !hab || hab.mode === 'atelier' || hab.rendu === 'atelier' ? 0 : (+hab.palier || 1);
      const sig = palier + '|' + JSON.stringify(hab && hab.jetons || {}) + '|' + ORIG.length;
      document.documentElement.dataset.habillage = String(palier || 'atelier');
      if (sig !== applique) { applique = sig;
      remettre();
      if (palier) {
        const J = hab.jetons || {}, AF = palier >= 2 ? ancrages(J, FG) : null, AB = palier >= 2 ? ancrages(J, BG) : null;
        const fondJeu = /^#[0-9a-f]{6}$/i.test(J['--nuit'] || '') ? lireCouleur(J['--nuit']) : [27, 28, 30, 1], texteJeu = /^#[0-9a-f]{6}$/i.test(J['--texte'] || '') ? lireCouleur(J['--texte']) : [214, 216, 219, 1];
        const parRegle = new Map();
        for (const o of ORIG) {
          let v = o.v; const texte = TEXTE.test(o.p), A = texte ? AF : AB;
          if (/radius$/.test(o.p) && palier === 1) v = v.replace(/(\d*\.?\d+)px/g, (m, n) => (+n > 4 && +n < 90 ? '4px' : m));
          else if ((o.p === 'box-shadow' || o.p === 'text-shadow') && palier === 1) v = /inset/.test(v) ? v : 'none';
          else if (o.p === 'font-family') v = polices(o.p, v, palier);
          if (o.p.startsWith('--') && palier >= 2 && /^#[0-9a-f]{6}$/i.test(J[o.p] || '')) v = J[o.p];      // jeton : valeur exacte de la DA
          else if (v === o.v || o.p === 'box-shadow' || /radius$/.test(o.p)) v = v.replace(COUL, m => { const c = lireCouleur(m); return ecrire(palier === 1 ? gris(c) : (A && A.length ? versJeu(c, A) : c)); });
          if (palier >= 2 && !o.p.startsWith('--')) { const r = parRegle.get(o.st) || {}; if (texte && o.p === 'color') r.fg = { o, v }; else if (/^background(-color|-image)?$/.test(o.p) && !r.bg) { const m = v.match(COUL); COUL.lastIndex = 0; if (m) r.bg = lireCouleur(m[0]); } parRegle.set(o.st, r); }
          if (v !== o.v) try { o.st.setProperty(o.p, v, o.pr); } catch (e) { /* rien */ }
        }
        // garde-fou de lisibilité : un texte et son fond dans la même règle gardent au moins 4,5:1
        for (const r of parRegle.values()) {
          if (!r.fg || !r.bg || r.bg[3] < .5) continue;
          const m = r.fg.v.match(COUL); COUL.lastIndex = 0; if (!m) continue;
          const c = lireCouleur(m[0]); if (contraste(c, r.bg) >= 4.5) continue;
          const mieux = [texteJeu, fondJeu, [255, 255, 255, 1], [17, 17, 17, 1]].sort((x, y) => contraste(y, r.bg) - contraste(x, r.bg))[0];
          try { r.fg.o.st.setProperty('color', ecrire([mieux[0], mieux[1], mieux[2], c[3]]), r.fg.o.pr); } catch (e) { /* rien */ }
        }
      }
      }
      // polices du jeu (palier 3+), logo (4+), décor (5) : refaits à chaque cycle (l'en-tête est réécrit par la page)
      let pol = $('#hab-polices'); if (!pol) { pol = document.createElement('style'); pol.id = 'hab-polices'; document.head.appendChild(pol); }
      const fmt = u => ({ ttf: 'truetype', otf: 'opentype', woff: 'woff', woff2: 'woff2' })[String(u).split('.').pop().toLowerCase()] || 'truetype';
      pol.textContent = palier >= 3 ? (hab.polices || []).filter(p => cheminSur(p.url, /^da\/[\w.-]+\.(ttf|otf|woff2?)$/i) && /^Jeu (Texte|Interface)$/.test(p.famille)).map(p => `@font-face{font-family:"${p.famille}";src:url("${p.url}") format("${fmt(p.url)}");font-display:swap}`).join('\n') : '';
      let logo = $('#hab-logo');
      const lg = palier >= 4 && hab.logo && hab.logo.fichier && cheminSur(hab.logo.fichier.url, /^da\/[\w.-]+\.(svg|png|webp|jpe?g)$/i) ? hab.logo.fichier.url : null;
      if (lg) { if (!logo) { logo = document.createElement('img'); logo.id = 'hab-logo'; logo.alt = ''; const n = $('#nom'); if (n) n.prepend(logo); } if (logo.getAttribute('src') !== lg) logo.src = lg; }
      else if (logo) logo.remove();
      const ico = palier >= 4 && hab.logo && hab.logo.icone && cheminSur(hab.logo.icone.url, /^da\/[\w.-]+\.(png|svg)$/i) ? hab.logo.icone.url : lg;
      let fav = document.querySelector('link[rel="icon"]#hab-icone');
      if (ico) { if (!fav) { fav = document.createElement('link'); fav.rel = 'icon'; fav.id = 'hab-icone'; document.head.appendChild(fav); } fav.href = ico; } else if (fav) fav.remove();
      const motif = palier >= 5 && hab.decor && hab.decor.motif && cheminSur(hab.decor.motif.url, /^da\/[\w.-]+\.(png|webp|jpe?g|svg)$/i) ? hab.decor.motif.url : null;
      document.body.classList.toggle('hab-motif', !!motif);
      if (motif) document.documentElement.style.setProperty('--hab-motif', `url("${motif}")`); else document.documentElement.style.removeProperty('--hab-motif');
      try { Bureau.redessinerFond && Bureau.redessinerFond(); } catch (e) { /* rien */ }
    }
    function peinture() { if (matchMedia('(prefers-reduced-motion: reduce)').matches) return; const d = document.createElement('div'); d.id = 'hab-peinture'; document.body.appendChild(d); setTimeout(() => d.remove(), 1900); }
    // thème du bureau (canevas) : maquette grise au palier 1 (désaturé), palette du jeu ensuite
    let cleTh = '', thMemo = null;
    function themeBureau(th) {
      const hab = D.hab, palier = STYLE_ATELIER || !hab || hab.mode === 'atelier' ? 0 : (+hab.palier || 1);
      const b = (palier >= 2 && hab.bureau) || {}, cle = (th && th.cle) + '|' + palier + '|' + JSON.stringify(b);
      if (cle === cleTh && thMemo) return thMemo;
      const o = Object.assign({}, th);
      if (palier >= 2) for (const k of ['mur', 'sol', 'bois', 'lumiere', 'accent', 'accent2']) if (/^#[0-9a-f]{6}$/i.test(b[k] || '')) o[k] = b[k];
      if (palier >= 2 && o.sol) o.sol2 = mix(o.sol, '#000000', .09);
      o.cle = String(th && th.cle) + '|h' + palier + JSON.stringify(b);
      cleTh = cle; thMemo = o; return o;
    }
    return { appliquer, peinture, themeBureau, palier: () => (STYLE_ATELIER || !D.hab || D.hab.mode === 'atelier') ? 0 : (+D.hab.palier || 1) };
  })();
  const mix = (a, b, k) => { const pa = parseInt(a.slice(1), 16), pb = parseInt(b.slice(1), 16); const c = i => Math.round(((pa >> i) & 255) + ((((pb >> i) & 255) - ((pa >> i) & 255)) * k)); return '#' + ((c(16) << 16) | (c(8) << 8) | c(0)).toString(16).padStart(6, '0'); };

  // mode du style choisi dans la page : effet tout de suite (le moteur réécrit habillage.json au passage suivant)
  function modeLocal(m) {
    const base = D.hab || { palier: 1 }; D.hab = Object.assign({}, base, { mode: m }); if (m !== 'atelier' && D.hab.rendu === 'atelier') delete D.hab.rendu;
    if (D.qe) D.qe.habillage = Object.assign({}, D.qe.habillage || {}, { mode: m });
    majTout();
  }
  // bandeau « maquette grise » (une ligne, dès la première minute) avec « Voir l'Atelier »
  function bandeauMaquette() {
    let b = $('#hab-maquette');
    const voir = Habillage.palier() === 1 && CONF.mode === 'travail' && !LS.get('hab_maquette_vu', false);
    if (!b) { if (!voir) return; b = nouveau('<div id="hab-maquette" role="note"><span></span><button type="button" class="bts" data-a></button><button type="button" class="x" aria-label="×">×</button></div>'); document.body.appendChild(b);
      b.querySelector('[data-a]').onclick = async () => { try { await poster('/api/reglages', { habillage_mode: 'atelier' }); REGLAGES.habillage_mode = 'atelier'; modeLocal('atelier'); toast(esc(t('q_atelier_actif'))); } catch (e) { toast(esc(e.message), { erreur: true }); } };
      b.querySelector('.x').onclick = () => { LS.set('hab_maquette_vu', true); b.hidden = true; };
      b.querySelector('.x').setAttribute('aria-label', t('fermer') || '×'); }
    b.hidden = !voir; if (voir) { const e = $('#entete'); b.style.top = Math.round((e ? e.getBoundingClientRect().bottom : 60) + 6) + 'px'; }
    b.querySelector('span').textContent = t('q_maquette'); b.querySelector('[data-a]').textContent = t('q_voir_atelier');
  }

  // ------------------------------------------------------------------ table du bureau : la maquette du projet (table_projet.json)
  // Dessin isométrique au canevas, dans le repère du bureau (iso(gx, gy, z)). Plateau 0..1 posé sur la table.
  const TableProjet = (() => {
    function sombre(c, k) { return mix(c, '#000000', k); } function clair(c, k) { return mix(c, '#ffffff', k); }
    const ok = c => /^#[0-9a-f]{6}$/i.test(c || '');
    function dessiner(G) {
      const tb = D.tab; if (!tb || !Array.isArray(tb.elements) || !tb.elements.length) return false;
      const { cx, iso, x0, y0, w, d, z0, T, anim } = G, zk = G.zk || 2.2;
      const P = (x, y, z = 0) => iso(x0 + x * w, y0 + y * d, z0 + z * zk);
      const poly = (pts, f, s) => { cx.beginPath(); pts.forEach((p, i) => i ? cx.lineTo(p[0], p[1]) : cx.moveTo(p[0], p[1])); cx.closePath(); if (f) { cx.fillStyle = f; cx.fill(); } if (s) { cx.strokeStyle = s; cx.lineWidth = .6; cx.stroke(); } };
      const bloc = (x, y, bw, bd, h, c, zb = 0) => {      // pavé : dessus, face avant gauche, face avant droite
        if (!ok(c)) c = '#9a958a';
        poly([P(x, y + bd, zb), P(x + bw, y + bd, zb), P(x + bw, y + bd, zb + h), P(x, y + bd, zb + h)], sombre(c, .22));
        poly([P(x + bw, y, zb), P(x + bw, y + bd, zb), P(x + bw, y + bd, zb + h), P(x + bw, y, zb + h)], sombre(c, .36));
        poly([P(x, y, zb + h), P(x + bw, y, zb + h), P(x + bw, y + bd, zb + h), P(x, y + bd, zb + h)], c, 'rgba(0,0,0,.12)');
      };
      const toit = (x, y, bw, bd, zb, h, c) => { const s = P(x + bw / 2, y + bd / 2, zb + h); poly([P(x, y + bd, zb), P(x + bw, y + bd, zb), s], sombre(c, .2)); poly([P(x + bw, y, zb), P(x + bw, y + bd, zb), s], sombre(c, .35)); };
      const ellipse = (x, y, rx, ry, z, c, a = 1) => { const [px, py] = P(x, y, z), [qx] = P(x + rx, y, z), [, qy] = P(x, y + ry, z); cx.save(); cx.globalAlpha *= a; cx.fillStyle = c; cx.beginPath(); cx.ellipse(px, py, Math.max(1, Math.abs(qx - px) * 1.2), Math.max(1, Math.abs(qy - py) * 1.2), 0, 0, 7); cx.fill(); cx.restore(); };
      try { const m = cx.getTransform(), [px, py] = P(.5, .5, 0), k = window.devicePixelRatio || 1; window.__tableProjet = { x: (m.a * px + m.c * py + m.e) / k, y: (m.b * px + m.d * py + m.f) / k, theme: tb.theme, detail: tb.detail }; } catch (e) { /* essais seulement */ }
      const els = tb.elements.slice(0, 80).filter(e => e && typeof e.type === 'string');
      const ordre = { socle: 0, terrain: 1, eau: 2, route: 3, relief: 4, phare: 6, vegetation: 6, unite: 7, lumiere: 8, brume: 9, etoiles: 9 };
      els.sort((a, b) => (ordre[a.type] - ordre[b.type]) || ((a.x + a.y) - (b.x + b.y)));
      for (const e of els) {
        const c = ok(e.couleur) ? e.couleur : '#9a958a', x = +e.x || 0, y = +e.y || 0, ew = +e.w || .05, ed = +e.h || .05, h = +e.z || .02;
        try {
          if (e.type === 'socle') bloc(-.02, -.02, 1.04, 1.04, h, c, -h);
          else if (e.type === 'terrain') { bloc(x, y, ew, ed, h, c); if (tb.detail >= 2) { cx.save(); for (let i = 0; i < 60; i++) { const a = Math.abs(Math.sin(i * 12.9898) * 43758.5453) % 1, b2 = Math.abs(Math.sin(i * 78.233) * 12345.678) % 1, [px, py] = P(x + a * ew, y + b2 * ed, h); cx.fillStyle = i % 3 ? 'rgba(0,0,0,.07)' : 'rgba(255,255,255,.06)'; cx.beginPath(); cx.ellipse(px, py, G.TW * .05, G.TW * .025, 0, 0, 7); cx.fill(); } cx.restore(); } }
          else if (e.type === 'relief') { const n = 4; for (let k = 0; k < n; k++) { const f = 1 - k / n, zz = .02 + h * k / n; ellipse(x + ew / 2, y + ed / 2 + .006, ew / 2 * f, ed / 2 * f, zz, sombre(c, .18)); ellipse(x + ew / 2, y + ed / 2, ew / 2 * f * .94, ed / 2 * f * .94, zz + h / n * .7, clair(mix(c, '#8fae7a', .35), .1 + k * .1)); } }
          else if (e.type === 'eau') {
            if (Array.isArray(e.trace) && e.trace.length > 1) {
              const pts = e.trace.filter(p => Array.isArray(p) && p.length === 2).map(([a, b]) => P(a, b, .022));
              cx.save(); cx.lineCap = 'round'; cx.lineJoin = 'round'; cx.strokeStyle = sombre(c, .25); cx.lineWidth = Math.max(2, G.TW * .09); cx.beginPath(); pts.forEach((p, i) => i ? cx.lineTo(p[0], p[1]) : cx.moveTo(p[0], p[1])); cx.stroke();
              cx.strokeStyle = c; cx.lineWidth = Math.max(1.5, G.TW * .065); cx.stroke();
              if (anim) { cx.setLineDash([G.TW * .05, G.TW * .12]); cx.lineDashOffset = -T * G.TW * .12; cx.strokeStyle = clair(c, .45); cx.lineWidth = Math.max(.8, G.TW * .018); cx.stroke(); }
              cx.restore();
            } else if (e.forme === 'cascade') { bloc(x, y, ew, ed * .2, h, c); }
            else { bloc(x, y, ew, ed, .012, c, .02); if (anim) { cx.save(); cx.globalAlpha = .35; for (let i = 0; i < 4; i++) { const k = (T * .15 + i / 4) % 1; ellipse(x + ew * (.15 + .7 * ((i * .37) % 1)), y + ed * k, ew * .06, ed * .02, .034, clair(c, .5)); } cx.restore(); } }
          } else if (e.type === 'route') { cx.save(); cx.strokeStyle = c; cx.lineWidth = Math.max(1, G.TW * .03); cx.setLineDash([G.TW * .06, G.TW * .04]); cx.beginPath(); const a = P(x, y, .023), b = P(x + ew * .5, y - .12, .023), q = P(x + ew, y, .023); cx.moveTo(a[0], a[1]); cx.quadraticCurveTo(b[0], b[1], q[0], q[1]); cx.stroke(); cx.restore(); }
          else if (e.type === 'phare') phare(e, c, x, y, ew, ed, h, { bloc, toit, poly, P, ellipse, cx, T, anim, G });
          else if (e.type === 'vegetation') {
            const [px, py] = P(x + ew / 2, y + ed / 2, .02), r = G.TW * (e.forme === 'sapin' ? .05 : .045), H = h * zk * G.TH * 1.6;
            cx.fillStyle = 'rgba(0,0,0,.18)'; cx.beginPath(); cx.ellipse(px + r * .4, py + r * .2, r, r * .45, 0, 0, 7); cx.fill();
            if (e.forme === 'sapin' || e.forme === 'pilier' || e.forme === 'antenne' || e.forme === 'lampadaire' || e.forme === 'cactus') { cx.fillStyle = e.forme === 'sapin' || e.forme === 'cactus' ? c : '#8a8578'; cx.beginPath(); cx.moveTo(px - r, py); cx.lineTo(px, py - H - r); cx.lineTo(px + r, py); cx.closePath(); cx.fill(); }
            else { cx.fillStyle = '#6b4a2e'; cx.fillRect(px - .8, py - H * .5, 1.6, H * .5); cx.fillStyle = c; cx.beginPath(); cx.arc(px, py - H * .55, r, 0, 7); cx.fill(); cx.fillStyle = clair(c, .2); cx.beginPath(); cx.arc(px - r * .3, py - H * .55 - r * .3, r * .45, 0, 7); cx.fill(); }
          } else if (e.type === 'unite') {
            const v = +e.vitesse || .03, k = anim ? T * v * 6 : 0, ux = .5 + (x - .5) * Math.cos(k) - (y - .5) * Math.sin(k) * .6, uy = .5 + (x - .5) * Math.sin(k) * .6 + (y - .5) * Math.cos(k);
            const [px, py] = P(clamp(ux, .06, .94), clamp(uy, .06, .94), .03); cx.fillStyle = 'rgba(0,0,0,.25)'; cx.beginPath(); cx.ellipse(px + 1, py + .5, 2.2, 1, 0, 0, 7); cx.fill(); cx.fillStyle = c; cx.fillRect(px - 1.2, py - 4, 2.4, 4); cx.beginPath(); cx.arc(px, py - 4.6, 1.3, 0, 7); cx.fill();
          } else if (e.type === 'lumiere') {
            if (e.forme === 'lumieres_fenetres') { const nuitK = (typeof nuit === 'function' && nuit()) ? 1 : .45; for (let i = 0; i < 7; i++) { const a = (Math.sin(i * 12.9898) * 43758.5453) % 1, b2 = (Math.sin(i * 78.233) * 12345.678) % 1; const fl = anim ? .5 + .5 * Math.sin(T * 2 + i * 1.7) : .8; const [px, py] = P(.25 + Math.abs(a) * .5, .25 + Math.abs(b2) * .5, .12); cx.fillStyle = `rgba(255,226,150,${(.5 * fl * nuitK).toFixed(2)})`; cx.beginPath(); cx.arc(px, py, 1.3, 0, 7); cx.fill(); } }
            else { const fl = anim ? .6 + .4 * Math.sin(T * (e.anime === 'flamme' ? 9 : 2.5)) : .9; const [px, py] = P(x + ew / 2, y + ed / 2, h); const g = cx.createRadialGradient(px, py, 0, px, py, G.TW * .12); g.addColorStop(0, `rgba(255,214,140,${(.85 * fl).toFixed(2)})`); g.addColorStop(1, 'rgba(255,214,140,0)'); cx.fillStyle = g; cx.beginPath(); cx.arc(px, py, G.TW * .12, 0, 7); cx.fill(); }
          } else if (e.type === 'brume') { const dx = anim ? Math.sin(T * .15) * .08 : 0; cx.save(); cx.globalAlpha = clamp(+e.opacite || .15, 0, .3); for (let i = 0; i < 3; i++) ellipse(.25 + i * .25 + dx, y + ed * (.3 + .2 * (i % 2)), .16, .07, .16, '#ffffff'); cx.restore(); }
          else if (e.type === 'etoiles') { for (let i = 0; i < 14; i++) { const fl = anim ? .4 + .6 * Math.abs(Math.sin(T * 1.3 + i)) : .8; const [px, py] = P((i * .137) % 1, (i * .291) % 1, .55); cx.fillStyle = `rgba(255,255,255,${(.7 * fl).toFixed(2)})`; cx.fillRect(px, py, 1.2, 1.2); } }
        } catch (err) { /* un élément fautif n'empêche pas les autres */ }
      }
      return true;
    }
    function phare(e, c, x, y, ew, ed, h, o) {
      const { bloc, toit, poly, P, ellipse, cx, T, anim, G } = o, tc = ok(e.toit) ? e.toit : sombre(c, .3), f = e.forme;
      if (f === 'chateau') {
        const tw = ew * .26, td = ed * .26;
        bloc(x, y, ew, ed, h * .55, c, .02);                                   // enceinte
        for (const [a, b] of [[0, 0], [ew - tw, 0], [0, ed - td], [ew - tw, ed - td]]) { bloc(x + a, y + b, tw, td, h * .78, clair(c, .04), .02); toit(x + a, y + b, tw, td, .02 + h * .78, h * .28, tc); }
        bloc(x + ew * .32, y + ed * .3, ew * .36, ed * .4, h * 1.1, clair(c, .08), .02); toit(x + ew * .32, y + ed * .3, ew * .36, ed * .4, .02 + h * 1.1, h * .35, tc);
        if (anim) { const [px, py] = P(x + ew * .5, y + ed * .5, .02 + h * 1.45); cx.strokeStyle = '#5c4f3f'; cx.lineWidth = .8; cx.beginPath(); cx.moveTo(px, py); cx.lineTo(px, py - 7); cx.stroke(); cx.fillStyle = tc; cx.beginPath(); cx.moveTo(px, py - 7); cx.lineTo(px + 5 + Math.sin(T * 4) * 1.2, py - 5.5); cx.lineTo(px, py - 4); cx.fill(); }
      } else if (['immeuble', 'tour', 'tour_balise', 'phare_marin', 'refuge', 'ferme', 'tribune', 'camp', 'salle', 'bloc', 'moulin'].includes(f)) {
        const dz = f === 'bloc' && anim ? .02 * Math.sin(T * 1.5 + x * 9) : 0;
        bloc(x, y, ew, ed, h, c, .02 + (f === 'bloc' ? .1 : 0) + dz);
        if (['immeuble', 'tour'].includes(f)) { cx.fillStyle = 'rgba(255,230,160,.55)'; for (let k = 1; k < 5; k++) { const [px, py] = P(x + ew, y + ed * .5, .02 + h * k / 5); cx.fillRect(px - 1, py - 1, 2, 1.6); } }
        if (['tour_balise', 'phare_marin', 'refuge', 'ferme', 'moulin', 'camp'].includes(f)) toit(x, y, ew, ed, .02 + h, h * .3, tc);
        if (f === 'moulin') { const [px, py] = P(x + ew / 2, y + ed, .02 + h * .8), a = anim ? T * 1.2 : .4; cx.strokeStyle = '#efe6d2'; cx.lineWidth = 1.4; for (let k = 0; k < 4; k++) { cx.beginPath(); cx.moveTo(px, py); cx.lineTo(px + Math.cos(a + k * Math.PI / 2) * G.TW * .1, py + Math.sin(a + k * Math.PI / 2) * G.TW * .1); cx.stroke(); } }
        if (f === 'salle') { const [px, py] = P(x + ew * .5, y + ed * .5, .02 + h); const fl = anim ? .6 + .4 * Math.sin(T * 9 + x * 7) : .9; cx.fillStyle = `rgba(255,170,80,${fl.toFixed(2)})`; cx.beginPath(); cx.arc(px, py, 1.6, 0, 7); cx.fill(); }
      } else if (f === 'vaisseau' || f === 'navire') {
        const dz = f === 'navire' && anim ? .01 * Math.sin(T * 1.6) : 0;
        bloc(x + ew * .1, y, ew * .8, ed, h * .6, c, .02 + dz); toit(x + ew * .7, y, ew * .3, ed, .02 + dz, h * .6, clair(c, .1)); bloc(x + ew * .3, y + ed * .25, ew * .25, ed * .5, h * .5, tc, .02 + h * .6 + dz);
        if (f === 'vaisseau' && anim) { const [px, py] = P(x + ew * .05, y + ed * .5, .02 + h * .3); const g = cx.createRadialGradient(px, py, 0, px, py, 6); g.addColorStop(0, `rgba(140,200,255,${(.6 + .3 * Math.sin(T * 6)).toFixed(2)})`); g.addColorStop(1, 'rgba(140,200,255,0)'); cx.fillStyle = g; cx.beginPath(); cx.arc(px, py, 6, 0, 7); cx.fill(); }
      } else if (f === 'sommet') { toit(x, y, ew, ed, .02, h, c); toit(x + ew * .32, y + ed * .32, ew * .36, ed * .36, .02 + h * .64, h * .36, ok(e.neige) ? e.neige : '#f4f6f8'); }
      else if (f === 'piste_boucle' || f === 'arene') {
        ellipse(x + ew / 2, y + ed / 2, ew * .42, ed * .42, .025, c); ellipse(x + ew / 2, y + ed / 2, ew * .3, ed * .3, .026, f === 'arene' ? sombre(c, .2) : '#7d9a5e');
        if (f === 'piste_boucle' && anim) { const a = T * .9, [px, py] = P(x + ew / 2 + Math.cos(a) * ew * .36, y + ed / 2 + Math.sin(a) * ed * .36, .03); cx.fillStyle = '#e2483a'; cx.fillRect(px - 2, py - 1.5, 4, 2.5); }
      } else if (f === 'plateau') { bloc(x, y, ew, ed, h, c, .02); cx.save(); cx.strokeStyle = 'rgba(0,0,0,.18)'; cx.lineWidth = .5; for (let k = 1; k < 6; k++) { const a = P(x + ew * k / 6, y, .02 + h), b = P(x + ew * k / 6, y + ed, .02 + h), a2 = P(x, y + ed * k / 6, .02 + h), b2 = P(x + ew, y + ed * k / 6, .02 + h); cx.beginPath(); cx.moveTo(a[0], a[1]); cx.lineTo(b[0], b[1]); cx.moveTo(a2[0], a2[1]); cx.lineTo(b2[0], b2[1]); cx.stroke(); } cx.restore(); }
      else if (f === 'carte') bloc(x, y, ew, ed, .008, c, .045);
      else if (f === 'ile' || f === 'oasis') { ellipse(x + ew / 2, y + ed / 2, ew / 2, ed / 2, .03, c); if (f === 'oasis') ellipse(x + ew / 2, y + ed / 2, ew * .2, ed * .2, .031, '#4f9fc0'); }
      else if (f === 'champ') { bloc(x, y, ew, ed, .006, c, .02); }
      else if (f === 'drapeau') { const [px, py] = P(x, y, .02), H = h * 1.6 * G.TH * 1.6; cx.strokeStyle = '#efe6d2'; cx.lineWidth = 1; cx.beginPath(); cx.moveTo(px, py); cx.lineTo(px, py - H); cx.stroke(); const ond = anim ? Math.sin(T * 5) * 1.5 : 0; cx.fillStyle = c; cx.beginPath(); cx.moveTo(px, py - H); cx.lineTo(px + 7, py - H + 2 + ond); cx.lineTo(px, py - H + 4.5); cx.fill(); }
      else bloc(x, y, ew, ed, h, c, .02);
    }
    // vue en grand (clic sur la table ou Journal des quêtes) : la même maquette, sur son propre canevas, animée
    function ouvrir() {
      if (!D.tab) return;
      Panneau.remplacer('maquette', el => {
        el.innerHTML = `<div class="surtitre">${esc(t('q_table'))} · ${esc(tf('q_table_d', { d: D.tab.detail }))}</div><h2>${esc(L(D.tab.nom_theme) || t('q_table'))}</h2><p class="discret">${esc(L(D.tab.description))}</p><canvas id="tp-vue" style="display:block;width:100%;aspect-ratio:16/10;border-radius:10px;background:radial-gradient(120% 100% at 50% 20%,#3a4652,#11161b)"></canvas>${D.tab.prochain_detail ? `<p class="discret">${esc(L(D.tab.prochain_detail))}</p>` : ''}`;
        const cv = el.querySelector('#tp-vue'), c = cv.getContext('2d');
        const tour = () => {
          if (!cv.isConnected) return;
          const k = window.devicePixelRatio || 1, W = cv.clientWidth, H = cv.clientHeight;
          if (cv.width !== Math.round(W * k)) { cv.width = Math.round(W * k); cv.height = Math.round(H * k); }
          c.setTransform(k, 0, 0, k, 0, 0); c.clearRect(0, 0, W, H);
          const w = 4, d = 3, TW = 2 * W * .78 / (w + d), TH = TW / 2, ox = W / 2 - (w - d) * TW / 4, oy = H / 2 - (w + d) * TH / 4 + TH * .9;
          const iso = (gx, gy, z = 0) => [ox + (gx - gy) * TW / 2, oy + (gx + gy) * TH / 2 - z * TH];
          c.fillStyle = 'rgba(0,0,0,.35)'; c.beginPath(); c.ellipse(W / 2, oy + (w + d) * TH / 4 + TH * 1.4, W * .38, TH * 1.6, 0, 0, 7); c.fill();
          dessiner({ cx: c, iso, TW, TH, x0: 0, y0: 0, w, d, z0: .35, zk: 1.8, T: performance.now() / 1000, anim: !matchMedia('(prefers-reduced-motion: reduce)').matches });
          requestAnimationFrame(tour);
        };
        requestAnimationFrame(tour);
      }, { large: false });
    }
    return { dessiner, ouvrir };
  })();
  window.TableProjet = TableProjet;

  // ------------------------------------------------------------------ gains d'XP : « +N XP » au milieu de l'écran, puis vers la barre
  // Toute hausse de l'XP du studio (tâche, quête, jalon, versement : roadmap + etat.json) est fêtée : rebond, compteur,
  // étincelles, petit son (muet et babillage respectés), envol vers la barre de l'en-tête qui se remplit, bannière de niveau.
  // Gains groupés s'ils arrivent ensemble ; jamais bloquant (clic pour passer) ; réglage « Gains d'XP » : complet, discret, coupé.
  const Xp = (() => {
    const CLE = 'xp_vu:' + (location.port || ''), file = [], raisons = [];
    let base = null, minuteur = 0, enCours = false, passer = null;
    const VUS = new Set(); let vusPret = false;                                // boutons déjà montrés (la bannière de niveau ne montre que les nouveaux)
    const mode = () => { const m = LS.get('xp_fete', 'complet'); return ['complet', 'discret', 'coupe'].includes(m) ? m : 'complet'; };
    const calme = () => (window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches) || LS.get('anim', true) === false;
    const niv = xp => Math.floor(Math.pow(Math.max(0, xp) / 100, .55)) + 1;
    const seuil = k => Math.ceil(100 * Math.pow(Math.max(0, k - 1), 1 / .55) - 1e-6);
    const pct = xp => { const n = niv(xp); return clamp(100 * (xp - seuil(n)) / Math.max(1, seuil(n + 1) - seuil(n)), 0, 100); };
    const lireXp = () => { try { return (typeof RM_C !== 'undefined' && RM_C && typeof ETAT !== 'undefined' && ETAT && typeof niveauStudio === 'function') ? niveauStudio().xp : null; } catch (e) { return null; } };
    const sonOk = () => { try { return !Son.coupe() && !document.hidden && !(typeof modeAbsent === 'function' && modeAbsent()); } catch (e) { return false; } };
    const babil = () => LS.get('babil_son', true) !== false;
    const attendre = ms => new Promise(r => { const t0 = setTimeout(r, ms); passer = () => { clearTimeout(t0); r(); }; });
    function raison(txt) { if (txt && raisons.length < 8 && !raisons.includes(txt)) raisons.push(String(txt).slice(0, 80)); }
    function verifier() {
      const xp = lireXp(); if (xp == null) return;
      if (!vusPret && D.qe) { vusPret = true; ((D.qe.deblocages && D.qe.deblocages.boutons) || []).forEach(b => b && b.id && VUS.add(b.id)); }
      if (base === null) { const vu = +LS.get(CLE, NaN); base = Number.isFinite(vu) && vu >= 0 && vu <= xp ? vu : xp; LS.set(CLE, base); }
      if (xp < base) { base = xp; LS.set(CLE, base); return; }        // roadmap réécrite : nouvelle base, rien à fêter
      if (xp > base) { clearTimeout(minuteur); minuteur = setTimeout(lancer, 700); }   // gains groupés
    }
    function lancer() {
      const xp = lireXp(); if (xp == null || xp <= base) return;
      file.push({ de: base, a: xp, raisons: raisons.splice(0) }); base = xp; LS.set(CLE, base); jouer();
    }
    function barre(xp, doux) {
      const b = $('#niv-xp'); if (!b) return;
      if (!doux) { b.style.transition = 'none'; b.style.width = pct(xp).toFixed(1) + '%'; void b.offsetWidth; b.style.transition = ''; }
      else b.style.width = pct(xp).toFixed(1) + '%';
    }
    function cible() {
      const n = $('#niveau'), r = n && !n.hidden ? n.getBoundingClientRect() : null;
      return r && r.width > 0 ? { x: r.left + r.width / 2, y: r.top + r.height / 2, el: n } : { x: innerWidth / 2, y: 0, el: null };
    }
    function etincelles(hote, n, grand) {
      if (calme()) return;
      for (let i = 0; i < n; i++) {
        const e = document.createElement('i'), a = (i / n) * Math.PI * 2 + Math.random() * .5, d = (grand ? 120 : 70) + Math.random() * (grand ? 120 : 70);
        e.style.setProperty('--dx', Math.round(Math.cos(a) * d) + 'px'); e.style.setProperty('--dy', Math.round(Math.sin(a) * d * .8) + 'px');
        e.style.animationDelay = Math.round(Math.random() * 120) + 'ms'; e.className = 'xf-e' + (i % 3 ? '' : ' b'); hote.appendChild(e);
      }
    }
    async function jouer() {
      if (enCours || !file.length) return;
      if (document.hidden) { document.addEventListener('visibilitychange', jouer, { once: true }); return; }
      enCours = true;
      const g = file.splice(0).reduce((acc, x) => ({ de: Math.min(acc.de, x.de), a: Math.max(acc.a, x.a), raisons: acc.raisons.concat(x.raisons) }), { de: Infinity, a: -Infinity, raisons: [] });
      try { await montrer(g); } catch (e) { erreur('gain d’XP', e); }
      passer = null; enCours = false; if (file.length) jouer();
    }
    async function montrer({ de, a, raisons: rs }) {
      const gain = a - de, nDe = niv(de), nA = niv(a), m = mode();
      if (m === 'coupe' || gain <= 0) return;
      barre(de, false);                                     // la barre attend que le gain arrive
      const vieux = $('#xp-fete'); if (vieux) vieux.remove();
      const hote = nouveau(`<div id="xp-fete" class="${m === 'discret' ? 'discret' : ''}" role="status" aria-live="polite"><div class="xf-carte" title="${esc(t('xp_passer'))}"><div class="xf-n">+0</div><div class="xf-xp">XP</div>${rs.length ? `<div class="xf-r">${esc(rs.slice(0, 3).join(' · '))}${rs.length > 3 ? ' …' : ''}</div>` : ''}</div></div>`);
      document.body.appendChild(hote);
      const carte = hote.querySelector('.xf-carte'), nb = hote.querySelector('.xf-n');
      let fini = false; carte.onclick = () => { fini = true; if (passer) passer(); };
      if (m === 'discret') { const c = cible(); hote.style.setProperty('--cx', c.x + 'px'); hote.style.setProperty('--cy', (c.y + 30) + 'px'); }
      // compteur qui défile jusqu'au nombre, petits tics (babillage)
      const duree = calme() || m === 'discret' ? 0 : Math.min(900, 320 + gain * 4), t0 = performance.now();
      if (m !== 'discret') etincelles(hote, 18, false);
      await new Promise(r => {
        let tic = 0;
        const pas = now => {
          const k = duree ? clamp((now - t0) / duree, 0, 1) : 1, v = Math.round(gain * (1 - Math.pow(1 - k, 3)));
          nb.textContent = '+' + v;
          if (sonOk() && babil() && m !== 'discret' && k < 1 && now - tic > 70) { tic = now; try { Son.bip(660 + 900 * k, .04, { type: 'triangle', gain: .012 }); } catch (e) { /* rien */ } }
          if (k < 1 && !fini) requestAnimationFrame(pas); else { nb.textContent = '+' + gain; r(); }
        };
        requestAnimationFrame(pas);
        passer = () => { nb.textContent = '+' + gain; r(); };      // clic : le compteur saute à la fin
        setTimeout(() => { nb.textContent = '+' + gain; r(); }, duree + 400);   // page sans images (onglet en arrière-plan) : le compteur finit quand même
      });
      if (sonOk()) try { Son.succes('petit'); } catch (e) { /* rien */ }
      if (!fini) await attendre(m === 'discret' ? 1200 : 650);
      // envol vers la barre d'XP de l'en-tête
      const c = cible(), r0 = carte.getBoundingClientRect();
      if (!calme() && !fini) {
        carte.style.animation = 'none';
        carte.style.transition = 'transform .62s cubic-bezier(.55,0,.75,.2), opacity .62s';
        carte.style.transform = `translate(${Math.round(c.x - (r0.left + r0.width / 2))}px,${Math.round(c.y - (r0.top + r0.height / 2))}px) scale(.22)`;
        carte.style.opacity = '.35';
        await attendre(620);
      }
      hote.remove();
      if (c.el) { c.el.classList.remove('xp-pulse'); void c.el.offsetWidth; c.el.classList.add('xp-pulse'); setTimeout(() => c.el.classList.remove('xp-pulse'), 1300); }
      if (nA > nDe) { const b = $('#niv-xp'); if (b) b.style.width = '100%'; await attendre(fini ? 0 : 750); barre(seuil(nA), false); }
      barre(a, true);
      if (nA > nDe) await niveau(nA, fini);
    }
    async function niveau(n, vite) {
      const rang = window.PALIER_NOM || (typeof RM_C !== 'undefined' && RM_C && RM_C.rang) || '';
      const tous = ((D.qe && D.qe.deblocages && D.qe.deblocages.boutons) || []).filter(b => b && b.id), nouv = tous.filter(b => !VUS.has(b.id)).map(b => L(b.libelle) || b.id);
      tous.forEach(b => VUS.add(b.id));                     // seulement ce qui est arrivé depuis la dernière bannière
      if (mode() === 'discret') { try { Succes.ajouter({ id: 'niveau-' + n, icone: '★', titre: tf('xp_niveau', { n }), sous: rang, taille: 'moyen' }); } catch (e) { /* rien */ } return; }
      const h = nouveau(`<div id="xp-fete" class="niveau" role="status" aria-live="polite"><div class="xf-carte" title="${esc(t('xp_passer'))}"><div class="xf-sur">${esc(t('xp_monte'))}</div><div class="xf-n">${esc(tf('xp_niveau', { n }))}</div>${rang ? `<div class="xf-r">${esc(tf('xp_rang', { r: rang }))}</div>` : ''}${nouv.length ? `<div class="xf-r">🔓 ${esc(nouv.slice(-2).join(' · '))}</div>` : ''}</div></div>`);
      document.body.appendChild(h); etincelles(h, 30, true);
      if (sonOk()) try { Son.succes('grand'); } catch (e) { /* rien */ }
      let fin = false; h.querySelector('.xf-carte').onclick = () => { fin = true; if (passer) passer(); };
      if (!vite) await attendre(2600);
      h.classList.add('sort'); await new Promise(r => setTimeout(r, fin || calme() ? 0 : 280)); h.remove();
    }
    return { verifier, raison, essai: (gain, r) => { const xp = lireXp() || 0; file.push({ de: Math.max(0, xp - gain), a: xp, raisons: r ? [r] : [] }); jouer(); }, base: () => base };
  })();
  window.addEventListener('studio:roadmap', () => setTimeout(() => { try { Xp.verifier(); } catch (e) { /* rien */ } }, 0));

  // ------------------------------------------------------------------ bulle « ! » dans la scène (au-dessus de l'assistant)
  window.Quetes = {
    themeBureau: th => { try { return Habillage.themeBureau(th); } catch (e) { return th; } },
    bulle: () => (actif() ? proposees().length : 0),
    soutien: nom => !!(D.cat && D.cat.agents && D.cat.agents[nom] && D.cat.agents[nom].soutien),
    ouvrirProposee: () => { const l = proposees(); if (l.length) ouvrirQuete(l[0].id); else ouvrirJournal(); },
    ouvrirJournal: () => ouvrirJournal(), ouvrir: id => ouvrirQuete(id),
    maj: () => majCycle(), palier: () => Habillage.palier(), etat: () => D, xp: Xp
  };

  // ------------------------------------------------------------------ cycle (appelé à la fin de chargerTout)
  let enCours = false;
  async function majCycle() {
    if (enCours) return; enCours = true;
    try {
      if (!D.cat) { const c = await lire('quetes.json'); if (c && Array.isArray(c.quetes)) { D.cat = c; PAR_ID = parId(); } }
      const [qe, hab, tab] = await Promise.all(['quetes_etat.json', 'habillage.json', 'table_projet.json'].map(lire));
      if (qe && typeof qe === 'object' && qe.quetes) { D.qe = qe; for (const id of Object.keys(OPT)) { const s = (qe.quetes[id] || {}).statut; if (s && s !== 'proposee') delete OPT[id]; } }
      if (hab && typeof hab === 'object') D.hab = hab;
      if (tab && typeof tab === 'object' && Array.isArray(tab.elements)) D.tab = tab;
      majTout();
    } catch (e) { erreur('quêtes', e); } finally { enCours = false; }
  }
  function majTout() {
    try { if (actif() && REGLAGES && REGLAGES.controle_modeles === undefined) REGLAGES.controle_modeles = false; } catch (e) { /* rien */ }
    try { Habillage.appliquer(D.hab); } catch (e) { erreur('habillage', e); }
    try { bandeauMaquette(); } catch (e) { erreur('maquette grise', e); }
    if (!D.cat || !D.qe) return;
    try { boutonsHaut(); ligneSuivie(); annonces(); } catch (e) { erreur('quêtes (page)', e); }
    try { Xp.verifier(); } catch (e) { erreur('gain d’XP', e); }
  }
  majCycle();
})();
