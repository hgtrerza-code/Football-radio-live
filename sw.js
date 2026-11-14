/* FootLive Pro : service worker prudent.
 * - Pages HTML : réseau d'abord (les scores et aperçus restent frais), copie en cache seulement si hors ligne.
 * - Fichiers statiques (CSS, JS, images, icônes) : cache d'abord, mis à jour en arrière-plan.
 * - Jamais de cache pour les API (Workers, ESPN, 365Scores, YouTube), les flux radio ni les requêtes non GET.
 * Pour forcer une mise à jour chez tous les visiteurs, changer VERSION.
 */
const VERSION = "2026-11-14-1";
const STATIC_CACHE = "flp-static-" + VERSION;
const PAGE_CACHE = "flp-pages-" + VERSION;
const PRECACHE = ["/favicon-192x192.png", "/competition.css", "/competition.js", "/i18n.js", "/404.html"];

self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(function (c) { return Promise.all(PRECACHE.map(function (u) { return c.add(u).catch(function () {}); })); })
      .then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys()
      .then(function (keys) {
        return Promise.all(keys.filter(function (k) { return k.indexOf("flp-") === 0 && k !== STATIC_CACHE && k !== PAGE_CACHE; })
          .map(function (k) { return caches.delete(k); }));
      })
      .then(function () { return self.clients.claim(); })
  );
});

function isStatic(url) {
  return /\.(?:css|js|png|jpg|jpeg|webp|svg|ico|woff2?)$/i.test(url.pathname);
}

self.addEventListener("fetch", function (event) {
  var req = event.request;
  if (req.method !== "GET") return;
  var url = new URL(req.url);
  if (url.origin !== self.location.origin) return;          // API tierces, radios, logos ESPN : on ne touche à rien
  if (url.pathname === "/sw.js" || url.pathname === "/matchs-du-jour.json") return;

  if (req.mode === "navigate" || (req.headers.get("accept") || "").indexOf("text/html") !== -1) {
    event.respondWith(
      fetch(req).then(function (res) {
        if (res && res.ok) { var copy = res.clone(); caches.open(PAGE_CACHE).then(function (c) { c.put(req, copy); }); }
        return res;
      }).catch(function () {
        return caches.match(req).then(function (hit) { return hit || caches.match("/404.html"); });
      })
    );
    return;
  }

  if (isStatic(url)) {
    event.respondWith(
      caches.match(req).then(function (hit) {
        var net = fetch(req).then(function (res) {
          if (res && res.ok) { var copy = res.clone(); caches.open(STATIC_CACHE).then(function (c) { c.put(req, copy); }); }
          return res;
        }).catch(function () { return hit; });
        return hit || net;
      })
    );
  }
});
