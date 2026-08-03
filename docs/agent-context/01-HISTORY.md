# 01-HISTORY — What was done (chronological)

Timeline of significant work. Dates approximate; the most recent session is 2026-08-03.

## v1.0.0 (2026-07-04) — initial feature set (see docs/CHANGELOG.md)
QR borrowing/returning with HMAC dynamic tokens, 3 roles (super admin, school admin/librarian,
student/teacher), gamification (XP/levels/achievements/challenges/streaks), grade promotion on
Sept 1, multi-language (uz/ru/en/karakalpak), glassmorphism UI + light/dark theme, Chart.js
statistics, Web Push notifications (VAPID), django-axes brute-force protection, CSV import/export,
CSP, password reset flow, SVGs.

## Session: refactor & cleanup (before 2026-08-03)
- **Sidebar consolidation**: single shared `apps/frontend/templates/frontend/shared/sidebar_items.html`
  used by all three panels; removed duplicated per-panel sidebars.
- **Soft delete** (`SoftDeleteMixin` in `apps/api/views/admin.py`): API delete ops became soft
  deletes; `SoftDeleteManager` in models; migrations `accounts/0012`, `books/0014`, `schools/0010`.
- **Audit history**: `HistoricalRecords` (django-simple-history) added to key models via the
  migrations above.
- **URL rework**: `apps/frontend/urls.py` rewritten; all patterns under `app_name='frontend'`;
  added missing `profile_edit` URL (`path('profile/edit/', ...)`).
- **`__all__` exports**: added to `apps/api/views/__init__.py` and `apps/api/serializers/__init__.py`
  (clears F401 import-star warnings without per-file ignores).
- **Lint cleanup**: fixed all remaining ruff issues (incl. ruff 0.16.0 formatter bug that corrupts
  `except (A, B):` — workaround is splitting except clauses; applied in `core/views.py`,
  `core/middleware.py`). `ruff check .` clean, `ruff format --check .` 152/152.
- **pyproject.toml**: removed 4 stale `per-file-ignores` (`frontend/urls.py`, `frontend/views/__init__.py`,
  `api/views/__init__.py`, `api/serializers/__init__.py`).
- **Verified**: 168 unit tests passing.

## Session: modernization to 2026 standards (2026-08-03) — MOST RECENT
Researched what comparable Django projects use in 2026 (DRF vs Ninja, Celery vs RQ/dramatiq, admin
themes, static pipelines, audit logging). Decisions: keep DRF, django-axes, django-simple-history,
Celery+Beat, jazzmin. Replace obsolete pieces:

- **`requirements.txt`**: removed `gunicorn==26.0.0` (dead — `start.sh` runs only `daphne`),
  removed `django-compressor==4.6.0` and `rcssmin==1.2.2`; swapped `psycopg2-binary>=2.9.9` →
  `psycopg[binary]>=3.2` (confirmed `dj-database-url` 2.3.0 maps `postgres://` to the plain
  `django.db.backends.postgresql` engine — psycopg v3 safe).
- **`core/settings.py`**: removed `'compressor'` from INSTALLED_APPS (jazzmin KEPT); removed
  `compressor.finders.CompressorFinder` from STATICFILES_FINDERS; deleted all `COMPRESS_*` settings;
  staticfiles backend → `whitenoise.storage.CompressedManifestStaticFilesStorage`.
- **Templates**: stripped `{% load compress %}` / `{% compress %}` from 11 files
  (`templates/base.html` [css+js blocks], `login`, `404`, `500`, `403`, `400`, `403_csrf`,
  `password_reset{,_confirm,_done,_complete}`); removed `?v=1.6` cache-busters from
  `{% static 'css/style.css' %}` and `?v=2` from `js/chart.umd.min.js` (4 frontend templates:
  user/profile, admin/dashboard, admin/statistics, school/dashboard).
- **Env**: uninstalled psycopg2-binary-2.9.12, django_compressor-4.6.0, rcssmin-1.2.2,
  gunicorn-26.0.0; installed psycopg-3.3.4 + psycopg-binary-3.3.4.
- **Fixed during verification**:
  - Removed broken `//# sourceMappingURL=chart.umd.js.map` line from `static/js/chart.umd.min.js`
    (manifest post-processing failed because the source map file doesn't exist).
  - `apps/frontend/templates/frontend/admin/profile.html` was missing `{% load frontend_tags %}`
    (used `action_name` filter) — pre-existing bug that would 500 the admin profile page; fixed.
  - `pyproject.toml` `testpaths` did NOT include `core` → core tests silently never ran in default
    pytest; added `"core"`. Now `pytest` collects 168.
- **Docs updated**: `AGENTS.md` (compressor gotchas → manifest-storage notes; test count 148→168),
  `docs/REQS.md` (`psycopg2-binary` → `"psycopg[binary]"`).
- **Verification results**: `manage.py check` 0 issues; `collectstatic --noinput --clear` OK (281
  files, hashed names in `staticfiles/staticfiles.json`); 168 unit tests green (1 harmless
  DeprecationWarning from pythonjsonlogger); `ruff check .` + `ruff format --check .` clean; all 75
  templates parse; smoke render of admin/school/user dashboards + news + my-books + profile +
  statistics + logs all HTTP 200 (student `/profile/` 302 is intended — it's `@superuser_required`).

## Session: dependency split + docs refresh (2026-08-03)
- **`requirements.txt`** now production-only; new **`requirements-dev.txt`** = `-r requirements.txt`
  + dev/test/lint tooling (`pytest`, `pytest-django`, `pytest-cov`, `ruff`, `pre-commit`,
  `pytest-playwright`, `playwright`). `django-extensions` stays in prod (it's in INSTALLED_APPS).
- Updated consumers: `Makefile` + `tasks.ps1` `install` targets (single `pip install -r
  requirements-dev.txt`), `.github/workflows/tests.yml` (lint/test/e2e jobs use
  `requirements-dev.txt`; prod image via `Dockerfile` unchanged — still `requirements.txt`).
- **`docs/CHANGELOG.md`**: added `v1.1.0 (2026-08-03)` covering the refactor + modernization work
  (soft-delete, history, sidebar, urls rework, static/psycopg migration, bug fixes, dependency split).
- **`README.md`**: dev setup now uses `requirements-dev.txt`; project structure updated
  (requirements files + `docs/agent-context/`).
- **Verified**: `pip install --dry-run -r requirements-dev.txt` resolves; `manage.py check` 0
  issues; `ruff check .` + `ruff format --check .` clean (156 files); `pytest` collects 168.

## Session: CI fix — postgres search (2026-08-03)
- Pushed the 5 commits; CI `lint` passed but `test`/`e2e` failed at **"Run migrations"** (Postgres).
- Root cause in the Postgres-only search feature (never ran locally — dev uses SQLite, CI was
  already red since `3433ecc`):
  - `books/migrations/0012` RunPython built an **invalid GIN index** SQL: `to_tsvector()` called
    with 7 args (missing `arg_joiner=' || '`), and `import django.contrib.postgres.indexes` had
    been dropped (AttributeError on Postgres).
  - `book_search_vector()` was **deleted from `books/models.py`** during the soft-delete work, but
    `books/search.py` imports it (`from .models import book_search_vector`) → ImportError at runtime
    on Postgres.
- Fixed: re-added the import + `arg_joiner=' || '` in the migration's add/remove functions; restored
  `book_search_vector()` in `books/models.py` with `output_field=models.TextField()` (Func with mixed
  types otherwise raises FieldError inside `SearchRank`).
- Verified: `book_search_vector()` compiles to `to_tsvector('simple', title || 'A' || author || 'B' ||
  description || 'C')`; `SearchRank` path compiles; fresh `migrate` from scratch on SQLite applies all
  migrations; `makemigrations --check` → no changes; ruff clean; books+api+core tests 158 passed.
- CI runs 2026-07-27 + 08-03 were failing for this reason; `e2e`/`test` should now go green.
