FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=core.settings

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gettext \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py compilemessages
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD gunicorn core.wsgi:application --bind 0.0.0.0:8000 --preload --timeout 120 --workers 4
