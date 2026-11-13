// Essai de la dictée : rejoue le cas réel du 13/11 sur le code extrait de la page.  node test_dictee.js <studio.html>
const fs = require('fs');
const page = fs.readFileSync(process.argv[2] || require('path').join(__dirname, '..', 'studio.html'), 'utf8');
const debut = page.indexOf('// DICTEE_PROPRE debut'), fin = page.indexOf('// DICTEE_PROPRE fin');
if (debut < 0 || fin < 0) { console.error('bloc DICTEE_PROPRE absent'); process.exit(1); }
const f = new Function(page.slice(debut, fin) + '; return { fusionSegments, dedoublonner, dicteePropre };')();
const ok = [], eq = (a, b, nom) => { if (a !== b) { console.error(`ÉCHEC ${nom} : « ${a} » au lieu de « ${b} »`); process.exit(1); } ok.push(nom); };
const attendu = 'faut que tu de faire une version portable';
eq(f.dicteePropre('faut faut que faut que tu de de faire de faire une de faire une version portable'), attendu, 'texte empilé');
eq(f.dicteePropre(['faut', 'faut que', 'faut que tu', 'de', 'de faire', 'de faire une', 'de faire une version portable']), attendu, 'finals cumulés');
eq(f.dicteePropre(['il faut que tu fasses', 'que tu fasses une version', 'une version portable']), 'il faut que tu fasses une version portable', 'recouvrements');
eq(f.dicteePropre("c'est très très bien, non non"), "c'est très très bien, non non", 'doublons voulus');
eq(f.dicteePropre('une phrase normale sans répétition'), 'une phrase normale sans répétition', 'phrase normale');
// reconnaissance du navigateur : événements successifs où les « finals » reprennent le début (Chrome Android)
const res = [];
const evt = l => ({ resultIndex: 0, results: l.map(t => Object.assign([{ transcript: t }], { isFinal: true })) });
for (const etape of [['faut'], ['faut', 'faut que'], ['faut', 'faut que', 'faut que tu'], ['faut', 'faut que', 'faut que tu', 'de faire une version portable']]) res.push(f.dicteePropre(evt(etape).results.filter(x => x.isFinal).map(x => x[0].transcript)));
eq(res[res.length - 1], 'faut que tu de faire une version portable', 'événements du navigateur');
console.log(`dictée : ${ok.length}/${ok.length} essais réussis`);
