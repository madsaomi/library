# Raqamli Kutubxona

School Library Management System built with Django + DRF.

## Quick Start

```bash
cp .env.example .env
docker compose up -d
```

Then apply migrations and create a superuser:

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Open http://localhost:8000

## Manual Setup (no Docker)

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements-dev.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

> `requirements.txt` is production-only; `requirements-dev.txt` (prod + test/lint tooling) is for local
> development and CI. Playwright browsers: `python -m playwright install chromium`.

## Project Structure

```
library/
├── apps/                    # Django applications (accounts, api, books, frontend, notifications, schools, stats)
├── core/                    # Django project core (settings, asgi, wsgi, urls)
├── docs/                    # Project documentation (agent-context/, REQS.md, SECURITY.md, CHANGELOG.md)
├── e2e/                     # End-to-end Playwright tests
├── templates/               # Global HTML templates
├── static/                  # Static assets (CSS, JS, images)
├── scripts/                 # Utility & helper scripts
├── requirements.txt         # Production dependencies
├── requirements-dev.txt     # + dev/test/lint tooling
└── manage.py                # Django management entrypoint
```

> **For AI agents**: read `docs/agent-context/00-START-HERE.md` first — it points to the full
> project state, history, and roadmap without needing to re-scan the codebase.

## Celery (Background Tasks)

```bash
celery -A core worker --loglevel=info
celery -A core beat --loglevel=info  # for periodic tasks
```

Production Celery broker: set `CELERY_BROKER_URL=redis://...` and `CELERY_RESULT_BACKEND=redis://...` in `.env`.

## E2E Tests

Playwright tests require **Python 3.13** (Python 3.14 has asyncio incompatibility with playwright):

```bash
# Install browsers once
python -m playwright install chromium

# Run E2E
pytest e2e/ -m e2e -v
```

## Production Checklist

- [ ] `DEBUG=False`
- [ ] `SECRET_KEY` set to a strong random value
- [ ] `ALLOWED_HOSTS` includes production domain
- [ ] `CSRF_TRUSTED_ORIGINS` includes production domain
- [ ] `DATABASE_URL` configured (PostgreSQL)
- [ ] `CHANNEL_LAYER_BACKEND=channels_redis.core.RedisChannelLayer` + `CHANNEL_LAYER_REDIS_URL`
- [ ] `CELERY_BROKER_URL` set to Redis
- [ ] `VAPID_PUBLIC_KEY` + `VAPID_PRIVATE_KEY` generated
- [ ] `SENTRY_DSN` set (optional)
- [ ] Static files collected (`collectstatic`)
- [ ] Migrations applied (`migrate`)
- [ ] `start.sh` used (daphne, not gunicorn)

## Tests

```bash
pytest --cov
```

### Quick Commands

| Command | Description |
|---------|-------------|
| `make help` | Show all available commands |
| `make test` | Run unit tests |
| `make lint` | Run ruff linter |
| `make format` | Auto-format code |
| `make runserver` | Start dev server |
| `make seed` | Seed test users |
| `make setup` | Full project setup |
| `make clean` | Remove cache & build artifacts |

**Windows (PowerShell):** Use `.\tasks.ps1 <command>` instead of `make`.

## Deployment (Railway)

Push to GitHub, connect in Railway. `DATABASE_URL` is auto-injected.

### Required Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `SECRET_KEY` | Django secret key | `change-me-in-production` |
| `DEBUG` | Debug mode | `False` |
| `ALLOWED_HOSTS` | Allowed hosts | `.railway.app` |
| `CSRF_TRUSTED_ORIGINS` | CSRF trusted origins | `https://*.railway.app` |
| `CHANNEL_LAYER_BACKEND` | WebSocket layer | `channels_redis.core.RedisChannelLayer` |
| `CHANNEL_LAYER_REDIS_URL` | Redis URL for channels | `redis://localhost:6379/1` |
| `VAPID_PUBLIC_KEY` | Push notifications | (generate with `python manage.py generate_vapid_keys`) |
| `VAPID_PRIVATE_KEY` | Push notifications | |
| `VAPID_ADMIN_EMAIL` | VAPID admin email | `admin@kutubxona.uz` |

### Deployment Notes

- Uses **daphne** (ASGI) not gunicorn — required for WebSocket support via Channels
- `start.sh` runs migrations, celery worker+beat, then `daphne`
- Celery uses Redis (set `CELERY_BROKER_URL` in production)
- Static files served via WhiteNoise
- CSP allows WebSockets: `ws://localhost:8000` dev, `wss://*.railway.app` prod

## API Docs

- Swagger: `/api/docs/`
- ReDoc: `/api/redoc/`
- OpenAPI schema: `/api/schema/`
