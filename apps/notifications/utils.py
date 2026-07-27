import json
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings

logger = logging.getLogger(__name__)


def send_push_notification(subscription, title, body, url=None):
    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        logger.warning('pywebpush not installed, skipping push notification')
        return False

    payload = json.dumps(
        {
            'title': title,
            'body': body,
            'url': url or '/',
        }
    )

    try:
        webpush(
            subscription_info={
                'endpoint': subscription.endpoint,
                'keys': {
                    'auth': subscription.auth_key,
                    'p256dh': subscription.p256dh_key,
                },
            },
            data=payload,
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={
                'sub': f'mailto:{settings.VAPID_ADMIN_EMAIL}',
            },
        )
        return True
    except WebPushException as e:
        if e.response and e.response.status_code in (410, 404):
            subscription.delete()
            logger.info(f'Removed expired subscription for {subscription.user}')
        else:
            logger.error(f'Push error: {e}')
        return False


def notify_user(user, title, body, url=None):
    from .models import Notification, PushSubscription

    notification = Notification.objects.create(user=user, title=title, body=body, url=url)

    unread_count = Notification.objects.filter(user=user, is_read=False).count()

    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f'notifications_{user.id}',
            {
                'type': 'send_notification',
                'id': notification.id,
                'title': title,
                'body': body,
                'url': url,
                'unread_count': unread_count,
            },
        )

    for sub in PushSubscription.objects.filter(user=user):
        send_push_notification(sub, title, body, url)
