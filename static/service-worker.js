self.addEventListener('install', event => {
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(clients.claim());
});

self.addEventListener('push', event => {
    const data = event.data.json();
    const options = {
        body: data.body,
        icon: '/static/img/icon.png',
        badge: '/static/img/badge.png',
        vibrate: [200, 100, 200],
        data: { url: data.url || '/' },
        actions: [
            { action: 'open', title: 'Ochish' },
            { action: 'close', title: 'Yopish' },
        ]
    };

    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

self.addEventListener('notificationclick', event => {
    event.notification.close();
    if (event.action === 'open' || event.action === undefined) {
        const url = event.notification.data.url || '/';
        event.waitUntil(clients.openWindow(url));
    }
});
