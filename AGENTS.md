# AGENTS.md — Online Kutibxona (School Library Management System)

## Project Overview
Django 6.0.7 + DRF school library management system with three user roles (superuser, school admin, student/teacher). Uses Channels (daphne) for WebSocket notifications, django-compressor for CSS/JS, and PostgreSQL on Railway.

## Architecture
- All Django apps (`accounts`, `api`, `books`, `frontend`, `notifications`, `schools`, `stats`) are located in `apps/` (added to `sys.path`).
- **Django app `frontend`** (in `apps/frontend/`) contains all three panels sharing one `app_name = 'frontend'` URL namespace:
  - `apps/frontend/views/admin_views.py` — superuser panel (URLs: `admin/...`, names like `admin_news_list`)
  - `apps/frontend/views/school_views.py` — school admin panel (URLs: `school/...`, names like `school_news_list`)
  - `apps/frontend/views/user_views.py` — student/teacher panel (URLs: `library/...`, names like `user_news_list`)
- **Templates**: `frontend/templates/frontend/admin/`, `school/`, `user/`
- **URL dispatch**: `apps/frontend/urls.py` has all patterns under `app_name = 'frontend'`
- **No** `frontend_admin:` or `frontend_school:` namespace prefixes exist — all redirects/urls use `frontend:` (e.g., `frontend:admin_news_list`)

## Key Gotchas

### URL names are NOT `news_list`
There is no `news_list` URL name. The correct names are:
- `frontend:admin_news_list` (admin panel)
- `frontend:school_news_list` (school panel)
- `frontend:user_news_list` (user/student panel)

### Django-compressor externals
External CDN URLs (Font Awesome, canvas-confetti) must be OUTSIDE `{% compress css %}` / `{% compress js %}` blocks. Putting them inside causes `UncompressableFileError`.

### Password reset templates
`{% compress css %}` must NOT wrap `<!DOCTYPE html>`. Structure should be:
```
{% load compress %}
<!DOCTYPE html>
<head>
{% compress css %}
<link ...>
{% endcompress %}
```

### Profile URL was missing
`profile_edit` view exists (`frontend/views/user_views.py` line 227) but had no URL pattern. Added via `path('profile/edit/', profile_edit, name='profile_edit')` in `frontend/urls.py`.

## Developer Commands
```bash
# Run dev server
$env:SECRET_KEY="django-insecure-test-key-not-for-production-environment-only"
$env:DEBUG="True"
python manage.py runserver

# Run tests (pytest, not Django test runner)
python -m pytest -q --tb=short

# Seed test users (5 roles with credentials printed)
python manage.py seed_test_users

# Lint + format
python -m ruff check .
python -m ruff format .

# Deploy: Railway uses `start.sh` → daphne (not gunicorn)
```

Automation shortcuts: **`make`** (Linux/macOS/Git Bash) or **`.\tasks.ps1`** (PowerShell).
See `Makefile` targets: `make help`, `make setup`, `make lint`, `make test`, `make runserver`, `make clean`.

## Deployment
- **Railway**: `start.sh` uses `daphne` (ASGI) + celery worker/beat
- **DB**: `DATABASE_URL` auto-injected on Railway; PostgreSQL locally via `docker compose`
- **Channels**: `CHANNEL_LAYER` uses InMemoryChannelLayer in dev; Redis in prod (set `CHANNEL_LAYER_BACKEND` + `CHANNEL_LAYER_REDIS_URL`)
- **CSP**: `CSP_CONNECT_SRC` includes `ws://localhost:8000` and `wss://*.railway.app` for WebSockets

## Test Users
After `python manage.py seed_test_users`:
| Role | Login | Password |
|------|-------|----------|
| superuser | admin | superadmin |
| school_admin | school_admin | admin123 |
| teacher | teacher | teacher123 |
| student | student | student123 |

## Test Infrastructure
- **pytest** with `pytest-django`, `pytest-playwright`
- Unit tests: `pytest` (148 tests in accounts, api, books, schools, stats)
- E2E tests: `pytest -m e2e` (14 Playwright tests in `e2e/`)
- CI runs unit tests on Python 3.14; E2E uses Python 3.13 (Python 3.14 has asyncio bug with playwright)
- Previously flaky test `books/tests.py::TestAchievements::test_award_borrow_xp` fixed by mocking `random.random`.
