from django.conf import settings


def vapid_key(request):
    return {
        'vapid_public_key': settings.VAPID_PUBLIC_KEY,
    }
