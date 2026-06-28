#!/bin/bash
set -e

python manage.py migrate --noinput
python manage.py ensure_admin

exec gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --preload --timeout 120 --workers 4
