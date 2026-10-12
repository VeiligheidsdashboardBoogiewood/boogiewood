// Offline-cache: altijd eerst het netwerk, bij geen verbinding de laatst bewaarde versie.
const CACHE = 'bw-v1';
const SHELL = ['./', 'index.html', 'd3.min.js', 'manifest.webmanifest', 'icons/icon-192.png', 'icons/icon-512.png', 'data/app.enc.json'];
self.addEventListener('install', (e) => { self.skipWaiting(); e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).catch(() => {})); });
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', (e) => {
  const u = new URL(e.request.url);
  if (e.request.method !== 'GET' || u.origin !== location.origin) return;
  const key = u.origin + u.pathname;
  e.respondWith(
    fetch(e.request).then((r) => { if (r.ok) { const cp = r.clone(); caches.open(CACHE).then((c) => c.put(key, cp)); } return r; })
      .catch(() => caches.match(key).then((m) => m || caches.match(u.origin + u.pathname.replace(/[^/]*$/, '') + 'index.html')))
  );
});
