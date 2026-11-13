// Service worker du studio : met en cache seulement la coquille de la page (HTML, scripts, styles, icônes, polices).
// Les données (*.json) et l'API (/api/...) ne passent jamais par le cache : toujours en direct.
// Réseau d'abord : sur PC on voit toujours la dernière version ; le cache ne sert que si le réseau manque.
const CACHE = 'studio-coquille-v1';
const COQUILLE = ['./studio.html', './manifest.webmanifest', './icone-192.png', './icone-512.png'];
self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(COQUILLE)).catch(() => {})); self.skipWaiting(); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(l => Promise.all(l.filter(x => x !== CACHE).map(x => caches.delete(x)))).then(() => self.clients.claim())); });
self.addEventListener('fetch', e => {
  const u = new URL(e.request.url);
  if (e.request.method !== 'GET' || u.origin !== self.location.origin) return;
  if (u.pathname.startsWith('/api/') || /\.json$/i.test(u.pathname)) return;                      // données : jamais en cache
  if (!(u.pathname === '/' || /\.(html|js|css|webmanifest|woff2?|ttf|otf)$/i.test(u.pathname) || /\/icone-\d+\.png$/.test(u.pathname))) return;
  e.respondWith(fetch(e.request).then(r => {
    if (r.ok && r.type === 'basic') { const c = r.clone(); caches.open(CACHE).then(x => x.put(e.request, c)).catch(() => {}); }
    return r;
  }).catch(() => caches.match(e.request, { ignoreSearch: true }).then(r => r || Response.error())));
});
