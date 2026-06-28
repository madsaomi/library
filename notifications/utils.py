import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def send_push_notification(subscription, title, body, url=None):
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        logger.warning("pywebpush not installed, skipping push notification")
        return False

    payload = json.dumps({
        "title": title,
        "body": body,
        "url": url or "/",
    })

    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {
                    "auth": subscription.auth_key,
                    "p256dh": subscription.p256dh_key,
                },
            },
            data=payload,
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={
                "sub": f"mailto:{settings.VAPID_ADMIN_EMAIL}",
            },
        )
        return True
    except WebPushException as e:
        if e.response and e.response.status_code in (410, 404):
            subscription.delete()
            logger.info(f"Removed expired subscription for {subscription.user}")
        else:
            logger.error(f"Push error: {e}")
        return False


def notify_user(user, title, body, url=None):
    from .models import Notification, PushSubscription

    Notification.objects.create(user=user, title=title, body=body, url=url)

    for sub in PushSubscription.objects.filter(user=user):
        send_push_notification(sub, title, body, url)
