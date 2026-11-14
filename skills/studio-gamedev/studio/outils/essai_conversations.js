// Essai sans navigateur des petites conversations (node studio/outils/essai_conversations.js) : détection de compile,
// métier et outil d'un poste, langue d'un titre, gabarits FR et EN alignés. Sort avec le code 1 au premier écart.
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm');
const src = fs.readFileSync(path.join(__dirname, '..', 'conversations.js'), 'utf8');
const ctx = { window: {}, location: { search: '' }, console };
vm.createContext(ctx); vm.runInContext(src, ctx);
const C = ctx.window.ConversationsStudio;
let err = 0, n = 0;
const egal = (quoi, obtenu, attendu) => { n++; if (obtenu !== attendu) { err++; console.log('ÉCART  ' + quoi + ' : ' + JSON.stringify(obtenu) + ' au lieu de ' + JSON.stringify(attendu)); } };

// ---- compile : ok, ko, ou rien à dire (null)
const COMPILE = [
  ['Build Godot : 0 erreur, export OK', 'ok'], ['Build échoue sur le shader, 3 erreurs', 'ko'], ['Compile verte', 'ok'],
  ['Le build passe', 'ok'], ['Le build ne passe pas', 'ko'], ['Le build ne passe plus', 'ko'], ['La compile ne passe jamais du premier coup', 'ko'],
  ["Le cook n'est plus vert", 'ko'], ['Rebuild échoue', 'ko'], ['Rebuild OK', 'ok'], ['Cook des plantes de la forêt', null],
  ['Build des vertex shaders', null], ['Je passe au build Android', null], ['Compilation sans erreur', 'ok'], ['Build : erreurs corrigées', 'ok'],
  ['Compile : 2 erreurs de link', 'ko'], ['Cook planté à 80 %', 'ko'], ['Le packaging plante au démarrage', 'ko'], ['Le build plante', 'ko'],
  ['Tests au vert après le build', 'ok'], ['Build cassé depuis ce matin', 'ko'], ['Préparer le build de la démo', null], ['Rouge à lèvres du PNJ, build demain', null],
  ['Build passes, 0 errors', 'ok'], ['Build failed with 2 errors', 'ko'], ["The build doesn't pass anymore", 'ko'], ['Build no longer compiles', 'ko'],
  ['Rebuild succeeded', 'ok'], ['Cooking the plant meshes', null], ['Build vertex colours', null], ['Packaging is green', 'ok'], ['Compile errors in the AI module', 'ko'],
  ['Moving on to the Android build', null], ['Build crashed at startup', 'ko'], ['Planter les arbres', null], ['Vertex paint de la mousse', null]
];
for (const [t, a] of COMPILE) egal('compile « ' + t + ' »', C.etatCompile(t), a);

// ---- métier et outil d'un poste
const S = { langue: () => 'fr', moteur: () => 'Godot', ls: { get: (k, d) => d, set() {} } };
const I = C.creer(S);
const POSTES = [
  [{ id: 'code', role: 'Code gameplay', mission: 'Prépare la logique sans moteur' }, 'code', null],
  [{ id: 'integration', role: 'Intégration moteur', mission: 'Branche le contenu dans le jeu' }, 'moteur', 'Godot'],
  [{ id: 'son', role: 'Son', mission: 'Créer et intégrer les sons' }, 'son', null],
  [{ id: 'modeles', role: 'Modélisation 3D', mission: 'Modèles dans Blender' }, 'modele3d', 'Blender'],
  [{ id: 'relecteur', role: 'Relecture', mission: 'Relit chaque tâche' }, 'relecture', null],
  [{ id: 'art', role: 'Direction artistique', mission: 'Planches de style, pas de Blender' }, 'direction', null],
  [{ id: 'ia', role: 'Comportements', mission: 'IA des créatures, sans Unreal' }, 'faune', null],
  [{ id: 'moteur2', role: 'Engine programmer', mission: 'Engine integration and tooling' }, 'moteur', 'Godot'],
  [{ id: 'tools', role: 'Gameplay code', mission: 'Engine-free logic, no engine needed' }, 'code', null]
];
for (const [p, cat, outil] of POSTES) { egal('métier de ' + p.id, I.categorie(p), cat); egal('outil de ' + p.id, I.outilDe(p), outil); }

// ---- langue d'un titre (null : le titre ne se décide pas seul, la langue du projet tranche)
const LANGUES = [['Rocher moussu', null], ['Cadrage', null], ['Lumière du sous-bois', 'fr'], ['Placer les arbres de la clairière', 'fr'],
  ['Build Godot : 0 erreur, export OK', null], ['Placing the trees in the clearing', 'en'], ['Lighting pass for the forest', 'en'], ['Nanite', null]];
for (const [t, l] of LANGUES) egal('langue « ' + t + ' »', C.langueDe(t), l);

// ---- gabarits : mêmes sujets, même nombre, mêmes données et même ordre des rôles dans les deux langues
const G = C.GABARITS, vars = l => l.map(x => (x.match(/\{\??\w+\}/g) || []).sort().join(',') + '|' + x.replace(/\{\?\w+\}/g, '')[0]).join(' ; ');
for (const s of new Set([...Object.keys(G.fr), ...Object.keys(G.en)])) {
  egal('nombre de gabarits « ' + s + ' »', (G.en[s] || []).length, (G.fr[s] || []).length);
  (G.fr[s] || []).forEach((g, i) => egal('gabarit ' + s + '#' + i, vars((G.en[s] || [])[i] || []), vars(g)));
}
console.log(err ? `ÉCHEC : ${err} écart(s) sur ${n} contrôles` : `OK : ${n} contrôles (compile ${COMPILE.length}, postes ${POSTES.length}, langues ${LANGUES.length}, gabarits FR = EN)`);
process.exit(err ? 1 : 0);
