# 00-START-HERE — Agent onboarding (read first)

You are an AI agent with **no conversation history** on this project. Do NOT scan the whole
codebase — that wastes your context budget. Read this folder in order, then `AGENTS.md`, and
only then open specific files.

## Read order
1. `00-START-HERE.md` (this file) — critical facts + what to skip
2. `01-HISTORY.md` — everything that was done so far
3. `02-CURRENT-STATE.md` — current verified state + gotchas
4. `03-ROADMAP.md` — what is planned next
5. `AGENTS.md` (repo root) — developer commands + key gotchas
6. Only then open the specific files you actually need.

## Project in one paragraph
"Online Kutubxona" — school library management system. **Django 6.0.7 + DRF**, Channels/daphne
(WebSockets), whitenoise `CompressedManifestStaticFilesStorage`, PostgreSQL (prod) / SQLite (dev),
Celery+Beat (background), django-axes (brute-force), django-simple-history (audit), jazzmin (admin
theme), pytest + Playwright (e2e). Deployed on Railway via `start.sh`.

## Critical facts (fast onboarding)
- All 7 Django apps live in `apps/` (added to `sys.path`): `accounts`, `api`, `books`, `frontend`,
  `notifications`, `schools`, `stats`. Import as `from accounts.models import ...`, NOT `apps.accounts`.
- The `frontend` app holds ALL three panels under ONE namespace `app_name = 'frontend'`:
  - `apps/frontend/views/admin_views.py` → URLs `admin/...`, names like `frontend:admin_news_list`
  - `apps/frontend/views/school_views.py` → URLs `school/...`, names like `frontend:school_news_list`
  - `apps/frontend/views/user_views.py` → URLs `library/...`, names like `frontend:user_news_list`
- **There is NO URL name `news_list`** — always the prefixed variants above.
- **Static pipeline has NO django-compressor** (`{% compress %}` was removed). Assets are plain
  `{% static '...' %}`. Backend is whitenoise `CompressedManifestStaticFilesStorage`.
  After changing CSS/JS run `python manage.py collectstatic --noinput` (hashed names via `staticfiles.json`).
- Tests run with **pytest** (not `manage.py test`). `testpaths` in `pyproject.toml` includes
  `core`. 168 unit tests + 14 e2e (CI only).
- Smoke-testing pages requires `HTTP_HOST='localhost'` in the test client (ALLOWED_HOSTS).

## What to NOT open first (waste of budget)
- `staticfiles/` (generated output)
- `db.sqlite3`, `static/manifest.json`-like generated artifacts
- `*/migrations/*` (only open if migration work is required)
- `e2e/` (Playwright, cannot run locally — CI only)
- `docs/REQS.md` (stale, historical spec)

## Commands (PowerShell / Windows)
```powershell
$env:SECRET_KEY="django-insecure-test-key-not-for-production-environment-only"; $env:DEBUG="True"
python manage.py runserver
python -m pytest -q --tb=short            # unit tests (168)
python -m pytest -m e2e                    # e2e — needs Python 3.13 + playwright, CI only
python -m ruff check .                     # lint
python -m ruff format .                    # format
python manage.py collectstatic --noinput   # after CSS/JS changes
python manage.py seed_test_users           # test users (admin/superadmin, school_admin/admin123, student/student123)
```
Automation: `make <target>` or `.\tasks.ps1 <target>` (help/install/lint/format/test/runserver/seed/clean).
