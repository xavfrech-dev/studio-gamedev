// Essai du micro de la dictée (bloc CAPTURE_MICRO de la page), avec un faux micro : ouvert une seule fois pour plusieurs
// dictées, sans traitement du navigateur, 0,8 s gardées avant le clic, WAV 16 kHz correct.   node test_capture.js <studio.html>
const fs = require('fs');
const page = fs.readFileSync(process.argv[2] || require('path').join(__dirname, '..', 'studio.html'), 'utf8');
const debut = page.indexOf('// CAPTURE_MICRO debut'), fin = page.indexOf('// CAPTURE_MICRO fin');
if (debut < 0 || fin < 0) { console.error('bloc CAPTURE_MICRO absent'); process.exit(1); }
const ok = [], eq = (a, b, nom) => { if (a !== b) { console.error(`ÉCHEC ${nom} : ${a} au lieu de ${b}`); process.exit(1); } ok.push(nom); };
// faux navigateur : micro à 48 kHz, nœud de traitement qu'on alimente à la main
let appels = [], noeuds = [], arrets = 0;
const piste = { stop() { arrets++; }, onended: null };
const navigator = { permissions: { query: async () => ({ state: 'granted' }) }, mediaDevices: { getUserMedia: async c => { appels.push(c); return { active: true, getAudioTracks: () => [piste], getTracks: () => [piste] }; } } };
class AudioContext { constructor() { this.sampleRate = 48000; this.state = 'running'; this.destination = {}; }
  createMediaStreamSource() { return { connect() {}, disconnect() {} }; }
  createScriptProcessor() { const n = { connect() {}, disconnect() {}, onaudioprocess: null }; noeuds.push(n); return n; }
  createGain() { return { gain: { value: 1 }, connect() {} }; } resume() { return Promise.resolve(); } close() {} }
const document = { addEventListener() {}, hidden: false };
const window = { AudioContext };
const Capture = new Function('navigator', 'window', 'document', 'Voix', page.slice(debut, fin) + '; return Capture;')(navigator, window, document, { actif: () => false });
const nourrir = s => { const n = noeuds[noeuds.length - 1]; for (let i = 0; i < s * 48000 / 4096; i++) n.onaudioprocess({ inputBuffer: { getChannelData: () => new Float32Array(4096).fill(0.25) } }); };
(async () => {
  eq(Capture.possible(), true, 'micro possible');
  await Capture.prechauffer();                     // survol du bouton : micro déjà autorisé, ouvert d'avance
  eq(appels.length, 1, 'ouverture au survol');
  const c = appels[0].audio; eq(c.echoCancellation === false && c.autoGainControl === false && c.noiseSuppression === false, true, 'aucun traitement du navigateur');
  nourrir(3);                                       // 3 s avant le clic : seules les 0,8 dernières sont gardées
  await Capture.ouvrir(); Capture.commencer();
  eq(appels.length, 1, 'clic sans nouvelle ouverture');
  eq(Math.abs(Capture.duree() - 0.8) < 0.1, true, 'tampon de 0,8 s avant le clic');
  nourrir(2);
  const a = Capture.terminer();
  eq(Math.abs(a.length / 16000 - 2.8) < 0.2, true, 'audio de la dictée (2,8 s : 0,8 avant + 2 pendant)');
  eq(Math.abs(a[100] - 0.25) < 1e-6, true, 'rééchantillonnage 48 → 16 kHz');
  const w = Capture.wav(a); eq(w.size, 44 + a.length * 2, 'taille du WAV');
  const b = Buffer.from(await w.arrayBuffer()); eq(b.toString('ascii', 0, 4) + b.toString('ascii', 8, 12), 'RIFFWAVE', 'en-tête WAV'); eq(b.readUInt32LE(24), 16000, 'WAV à 16 kHz');
  await Capture.ouvrir(); Capture.commencer(); nourrir(1); Capture.terminer();   // deuxième dictée dans la session
  eq(appels.length, 1, 'deuxième dictée sans rouvrir le micro');
  eq(arrets, 0, 'micro jamais coupé entre deux dictées');
  let auto = 0; Capture.commencer(() => auto++); nourrir(241); eq(auto, 1, 'arrêt automatique à 4 min'); Capture.terminer();
  Capture.fermer(); eq(arrets, 1, 'fermeture du micro'); eq(Capture.ouvert(), false, 'micro fermé');
  console.log(`capture : ${ok.length}/${ok.length} essais réussis`);
})().catch(e => { console.error('ÉCHEC', e); process.exit(1); });
