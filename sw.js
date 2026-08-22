var CACHE = 'nnn-202608222127';
var SHELL = ['/', '/assets/site.css', '/assets/pages.js', '/assets/filter.js',
             '/offline.html', '/assets/icon-192.png'];
self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(SHELL); })
    .then(function () { return self.skipWaiting(); }));
});
self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k !== CACHE; })
      .map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});
self.addEventListener('fetch', function (e) {
  var url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;
  // Live data and the portfolio backend must never be cache-served.
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/portfolio')) return;
  if (url.pathname.startsWith('/assets/')) {
    // Stale-while-revalidate: paint from cache instantly, refresh it in the
    // background so the next load is never more than one build behind.
    e.respondWith(caches.match(e.request).then(function (hit) {
      var refresh = fetch(e.request).then(function (res) {
        var copy = res.clone();
        caches.open(CACHE).then(function (c) { c.put(e.request, copy); });
        return res;
      }).catch(function () { return hit; });
      return hit || refresh;
    }));
    return;
  }
  e.respondWith(fetch(e.request).then(function (res) {
    var copy = res.clone();
    caches.open(CACHE).then(function (c) { c.put(e.request, copy); });
    return res;
  }).catch(function () {
    return caches.match(e.request).then(function (hit) {
      return hit || caches.match('/offline.html');
    });
  }));
});