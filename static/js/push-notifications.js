var applicationServerKey = window.VAPID_PUBLIC_KEY || '';

function urlBase64ToUint8Array(base64String) {
    var padding = '='.repeat((4 - base64String.length % 4) % 4);
    var base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    var rawData = window.atob(base64);
    return new Uint8Array([].map.call(rawData, function(ch) { return ch.charCodeAt(0); }));
}

async function registerServiceWorker() {
    if (!('serviceWorker' in navigator)) return null;
    try {
        var registration = await navigator.serviceWorker.register('/service-worker.js', { scope: '/' });
        return registration;
    } catch (err) {
        console.error('SW registration failed:', err);
        return null;
    }
}

async function subscribeToPush(registration) {
    if (!registration || !applicationServerKey) return;

    try {
        var subscription = await registration.pushManager.getSubscription();

        if (!subscription) {
            subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(applicationServerKey),
            });
        }

        await fetch('/api/notifications/subscribe/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify(subscription.toJSON()),
        });
    } catch (err) {
        console.error('Push subscription failed:', err);
    }
}

function getCookie(name) {
    var value = '; ' + document.cookie;
    var parts = value.split('; ' + name + '=');
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
}

document.addEventListener('DOMContentLoaded', async function() {
    var registration = await registerServiceWorker();
    if (applicationServerKey) {
        subscribeToPush(registration);
    }
});
