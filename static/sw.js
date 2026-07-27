const CACHE_NAME = 'kutubxona-cache-v1';
const STATIC_ASSETS = [
    '/offline/',
    '/static/css/index.css',
    '/static/img/icon-192.svg',
    '/static/img/icon-512.svg'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS).catch(err => console.log('Static asset caching failed', err));
        })
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.filter(name => name !== CACHE_NAME).map(name => caches.delete(name))
            );
        })
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    // Only handle GET requests
    if (event.request.method !== 'GET') return;

    // Ignore chrome-extension and ws requests
    if (!event.request.url.startsWith('http')) return;

    event.respondWith(
        fetch(event.request)
            .then(response => {
                // Network First for HTML pages
                if (event.request.headers.get('accept').includes('text/html')) {
                    const clonedRes = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(event.request, clonedRes));
                }
                return response;
            })
            .catch(() => {
                // If offline
                return caches.match(event.request).then(cachedResponse => {
                    if (cachedResponse) {
                        return cachedResponse;
                    }
                    // If HTML page request and not in cache, show offline page
                    if (event.request.headers.get('accept').includes('text/html')) {
                        return caches.match('/offline/');
                    }
                    return new Response('', { status: 408, headers: { 'Content-Type': 'text/plain' } });
                });
            })
    );
});
