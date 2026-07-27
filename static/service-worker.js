var CACHE_NAME = 'kutubxona-v1';
var STATIC_URLS = [
  '/static/css/style.css',
  '/static/js/htmx.min.js',
  '/static/js/push-notifications.js',
  '/static/js/level-up.js',
  '/static/img/icon.svg',
  '/static/img/badge.svg',
  '/static/favicon.svg',
  '/static/manifest.json',
  '/offline/',
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(STATIC_URLS);
    }).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(names => {
      return Promise.all(
        names.filter(n => n !== CACHE_NAME).map(n => caches.delete(n))
      );
    })
  );
  event.waitUntil(clients.claim());
});

self.addEventListener('fetch', event => {
  var url = new URL(event.request.url);

  if (event.request.method !== 'GET') return;

  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkOnly(event.request));
    return;
  }

  if (STATIC_URLS.includes(url.pathname) || url.pathname.match(/\.(css|js|svg|png|jpg|woff2?)$/)) {
    event.respondWith(cacheFirst(event.request));
    return;
  }

  if (url.pathname === '/' || !url.pathname.match(/\.\w+$/)) {
    event.respondWith(networkFirst(event.request));
    return;
  }

  event.respondWith(networkOnly(event.request));
});

function cacheFirst(request) {
  return caches.match(request).then(cached => {
    return cached || fetch(request).then(function(response) {
      return caches.open(CACHE_NAME).then(function(cache) {
        cache.put(request, response.clone());
        return response;
      });
    }).catch(function() {
      return new Response('Offline', { status: 503 });
    });
  });
}

function networkFirst(request) {
  return fetch(request).then(function(response) {
    return caches.open(CACHE_NAME).then(function(cache) {
      cache.put(request, response.clone());
      return response;
    });
  }).catch(function() {
    return caches.match(request).then(function(cached) {
      return cached || caches.match('/offline/');
    });
  });
}

function networkOnly(request) {
  return fetch(request).catch(function() {
    return new Response(JSON.stringify({ error: 'offline' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
    });
  });
}

self.addEventListener('push', event => {
  if (!event.data) return;
  try {
    var data = event.data.json();
    var options = {
      body: data.body,
      icon: '/static/img/icon.svg',
      badge: '/static/img/badge.svg',
      vibrate: [200, 100, 200],
      data: { url: data.url || '/' },
      actions: [
        { action: 'open', title: 'Ochish' },
        { action: 'close', title: 'Yopish' },
      ]
    };
    event.waitUntil(self.registration.showNotification(data.title, options));
  } catch(e) {}
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  if (event.action === 'open' || event.action === undefined) {
    var url = event.notification.data.url || '/';
    event.waitUntil(clients.openWindow(url));
  }
});
