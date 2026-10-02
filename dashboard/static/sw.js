// JARVIS Dashboard — service worker
//
// Purpose: let the dashboard be installed to a home screen / app list and open
// instantly, full-screen, even on a flaky connection — NOT to run JARVIS
// offline. Voice/chat/commands always need the paired desktop JARVIS reachable
// over the network; nothing here changes that.
//
// Strategy:
//   • App shell (/, /login, icons, manifest, crypto.js) — cached so the app
//     has something to show the instant it opens, before the network reply
//     lands.
//   • HTML pages use NETWORK-FIRST: always try the live page first (it carries
//     this session's IP/port text and auth bounce logic), and only fall back
//     to the cached copy if the network request fails outright — so an
//     online user is never shown stale HTML.
//   • Static assets (icons, crypto.js, manifest) use CACHE-FIRST — they don't
//     change between releases, so skip the network once cached.
//   • Everything else (POST /login, /api/*, WebSocket upgrades) is left
//     completely alone. Bump CACHE_NAME to invalidate old caches on update.

const CACHE_NAME = 'jarvis-dashboard-v1';
const APP_SHELL = [
  '/',
  '/login',
  '/manifest.json',
  '/static/crypto.js',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/static/icons/apple-touch-icon.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(
        names.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n))
      ))
      .then(() => self.clients.claim())
  );
});

function isNavigationRequest(req) {
  return req.mode === 'navigate' ||
    (req.method === 'GET' && req.headers.get('accept')?.includes('text/html'));
}

self.addEventListener('fetch', (event) => {
  const req = event.request;

  // Never touch non-GET requests (login POST, /api/*, uploads) or any
  // cross-origin request — only this app's own GETs are ever cached.
  if (req.method !== 'GET' || new URL(req.url).origin !== self.location.origin) {
    return;
  }

  // HTML shell: network-first, cache as a fallback.
  if (isNavigationRequest(req)) {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, copy));
          return res;
        })
        .catch(() => caches.match(req).then((res) => res || caches.match('/')))
    );
    return;
  }

  // Static assets under /static/: cache-first.
  if (new URL(req.url).pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(req).then((cached) => cached || fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(req, copy));
        return res;
      }))
    );
    return;
  }

  // Everything else (api calls, websockets, uploads): default browser behavior.
});
