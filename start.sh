#!/bin/bash
set -e

python manage.py migrate --noinput
python manage.py ensure_admin
python manage.py collectstatic --noinput --clear

# Start Celery worker in background
celery -A core worker --loglevel=info --concurrency=2 &
celery -A core beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler &

# ASGI server with Daphne for WebSocket + HTTP support
exec daphne -b 0.0.0.0 -p $PORT core.asgi:application
