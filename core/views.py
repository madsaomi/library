import platform
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import FileResponse, JsonResponse
from django.shortcuts import render


def csrf_failure(request, reason=''):
    return render(request, '403_csrf.html', status=403)


def offline_view(request):
    return render(request, 'offline.html')


def service_worker(request):
    sw_path = Path(settings.BASE_DIR) / 'static' / 'service-worker.js'
    response = FileResponse(sw_path.open('rb'), content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    return response


def health_check(request):
    checks = {}
    all_ok = True

    try:
        connection.ensure_connection()
        checks['database'] = 'ok'
    except Exception as e:
        checks['database'] = str(e)
        all_ok = False

    try:
        cache.set('health_check', 1, 5)
        cache.get('health_check')
        checks['cache'] = 'ok'
    except Exception as e:
        checks['cache'] = str(e)
        all_ok = False

    try:
        import redis

        redis_url = getattr(settings, 'REDIS_URL', None) or getattr(settings, 'CHANNEL_LAYER_REDIS_URL', None)
        if redis_url:
            r = redis.from_url(redis_url, socket_connect_timeout=2)
            r.ping()
            checks['redis'] = 'ok'
        else:
            checks['redis'] = 'not_configured'
    except Exception as e:
        checks['redis'] = str(e)
        all_ok = False

    try:
        from celery import current_app

        current_app.control.ping(timeout=2)
        checks['celery'] = 'ok'
    except Exception as e:
        checks['celery'] = str(e)
        all_ok = False

    status_code = 200 if all_ok else 503
    return JsonResponse(
        {
            'status': 'ok' if all_ok else 'degraded',
            'checks': checks,
            'version': getattr(settings, 'APP_VERSION', '1.0.0'),
            'python': platform.python_version(),
        },
        status=status_code,
    )
