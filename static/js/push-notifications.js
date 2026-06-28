const applicationServerKey = window.VAPID_PUBLIC_KEY || '';

function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    return new Uint8Array([...rawData].map(ch => ch.charCodeAt(0)));
}

async function subscribeToPush() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        console.log('Push notifications not supported');
        return;
    }
    if (!applicationServerKey) return;

    try {
        const registration = await navigator.serviceWorker.register('/static/service-worker.js');
        let subscription = await registration.pushManager.getSubscription();

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
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
}

// Auto-subscribe on page load (if VAPID keys are configured)
document.addEventListener('DOMContentLoaded', () => {
    if (applicationServerKey) {
        subscribeToPush();
    }
});
