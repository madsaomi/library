import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import PushSubscription, Notification


@login_required
@require_POST
@csrf_exempt
def subscribe(request):
    data = json.loads(request.body)
    sub, created = PushSubscription.objects.update_or_create(
        user=request.user,
        endpoint=data.get("endpoint"),
        defaults={
            "auth_key": data.get("keys", {}).get("auth", ""),
            "p256dh_key": data.get("keys", {}).get("p256dh", ""),
        },
    )
    return JsonResponse({"status": "ok", "created": created})


@login_required
@require_POST
@csrf_exempt
def unsubscribe(request):
    data = json.loads(request.body)
    PushSubscription.objects.filter(
        user=request.user, endpoint=data.get("endpoint")
    ).delete()
    return JsonResponse({"status": "ok"})


@login_required
def list_notifications(request):
    notifications = Notification.objects.filter(user=request.user)[:50]
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({
        "unread_count": unread_count,
        "notifications": [
            {
                "id": n.id,
                "title": n.title,
                "body": n.body,
                "url": n.url,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat(),
            }
            for n in notifications
        ],
    })


@login_required
@require_POST
def mark_read(request, notification_id):
    Notification.objects.filter(id=notification_id, user=request.user).update(is_read=True)
    return JsonResponse({"status": "ok"})


@login_required
@require_POST
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({"status": "ok"})


@login_required
def unread_count(request):
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({"unread_count": count})


@login_required
def top_notification_api(request):
    note = Notification.objects.filter(
        user=request.user, is_read=False
    ).order_by('-created_at').first()
    if note:
        return JsonResponse({
            "id": note.id,
            "title": note.title,
            "body": note.body,
            "url": note.url,
        })
    return JsonResponse(None, safe=False)
