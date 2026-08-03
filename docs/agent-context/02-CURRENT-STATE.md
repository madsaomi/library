# 02-CURRENT-STATE — What is true right now

Last fully verified: 2026-08-03 (after the modernization + dependency-split session).

## Green (verified)
- `python manage.py check` → 0 issues
- `python manage.py collectstatic --noinput --clear` → works, 281 files, hashed names via
  `staticfiles/staticfiles.json` (manifest storage active)
- `python -m pytest -q --tb=short` → **168 passed** (1 harmless DeprecationWarning from
  `pythonjsonlogger` in site-packages)
- `python -m ruff check .` → all passed; `ruff format --check .` → 156 files already formatted
- `pip install --dry-run -r requirements-dev.txt` → resolves cleanly
- All 75 templates parse (`get_template` for every `templates/*.html` + frontend templates)
- Smoke render (test client, `HTTP_HOST='localhost'`): `/admin/`, `/admin/news/`, `/profile/`,
  `/admin/statistics/`, `/admin/logs/`, `/school/`, `/school/news/`, `/library/`,
  `/library/news/`, `/library/my-books/` all 200. Student hitting `/profile/` gets 302 (intended —
  that view is `@superuser_required`).

## Dependencies (as of now)
- **`requirements.txt`** — production only (used by `Dockerfile`/Railway): Django 6.0.7, DRF 3.16,
  djangorestframework-simplejwt, drf-spectacular, `psycopg[binary]>=3.2` (v3, NOT psycopg2),
  whitenoise 6.12, jazzmin, django-axes, django-csp, celery[redis]+django-celery-beat, sentry-sdk,
  qrcode, Pillow, dj-database-url, openpyxl, reportlab, django-filter, pywebpush, py-vapid, channels,
  channels-redis, daphne, django-extensions (used in INSTALLED_APPS), django-simple-history,
  python-json-logger.
- **`requirements-dev.txt`** — `-r requirements.txt` + pytest, pytest-django, pytest-cov, ruff,
  pre-commit, pytest-playwright, playwright. Used by Makefile/tasks.ps1/CI for local dev and tests.
- **No** gunicorn / django-compressor / rcssmin / psycopg2 anywhere in code or deps.

## Settings / static
- `core/settings.py` STORAGES: `'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'}`
- No `{% compress %}` tags anywhere; CDN assets (Font Awesome 6.4.0 cdnjs, canvas-confetti jsdelivr)
  are plain `<link>`/`<script>` tags.
- `static/js/htmx.min.js` is vendored and base.html uses HTMX (hx-boost/hx-target).

## Runtime environment notes
- Local: Windows + PowerShell 5.1, Python 3.12.10, pip 25.0.1, DB = SQLite (`db.sqlite3`) by
  default; Postgres via `docker compose` (prod / CI use Postgres).
- CI (.github/workflows/tests.yml): lint+test on Python 3.14, e2e on Python 3.13, Postgres 16 service.
- Env vars needed for any Django command locally:
  `$env:SECRET_KEY="django-insecure-test-key-not-for-production-environment-only"; $env:DEBUG="True"`
- E2E (`pytest -m e2e`, 14 tests) requires Playwright + Python 3.13 — cannot run locally.

## Known gotchas (important)
- URL names are prefixed: `frontend:admin_news_list` / `frontend:school_news_list` /
  `frontend:user_news_list` — never bare `news_list`.
- Import apps as `from <app>.models import ...` (apps/ is on `sys.path`), not `apps.<app>`.
- ruff 0.16.0 formatter can corrupt `except (A, B):` → split into separate `except` clauses.
- Manifest storage fails loudly if a referenced static file is missing (post-processing follows
  references inside CSS/JS) — that's why `chart.umd.min.js` had its sourcemap line removed.
- Test client needs `HTTP_HOST='localhost'` for ALLOWED_HOSTS.

## Recently changed files (this is the "diff to trust")
- `requirements.txt` (now prod-only), `requirements-dev.txt` (new)
- `core/settings.py`
- `templates/base.html`, `templates/login.html`, `templates/404.html`, `templates/500.html`,
  `templates/403.html`, `templates/400.html`, `templates/403_csrf.html`,
  `templates/password_reset.html`, `templates/password_reset_confirm.html`,
  `templates/password_reset_done.html`, `templates/password_reset_complete.html`
- `static/js/chart.umd.min.js` (sourcemap line removed)
- `apps/frontend/templates/frontend/admin/profile.html` (added `{% load frontend_tags %}`)
- `apps/frontend/templates/frontend/user/profile.html`, `admin/dashboard.html`,
  `admin/statistics.html`, `school/dashboard.html` (`?v=2` removed)
- `pyproject.toml` (testpaths + core; per-file-ignores cleanup), `AGENTS.md`, `docs/REQS.md`
- `Makefile`, `tasks.ps1`, `.github/workflows/tests.yml` (install `requirements-dev.txt`)
- `README.md`, `docs/CHANGELOG.md`, `docs/agent-context/`
