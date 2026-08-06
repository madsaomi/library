# 02-CURRENT-STATE — What is true right now

Last fully verified: 2026-08-07 (unified QR system + scanner redesign + design system across all ~90 templates + 169 tests).

## 2026-08-06 — design-system rollout complete
- **All templates** in `apps/frontend/templates/frontend/{admin,school,user,shared}` (~90) redesigned to the
  unified system in `docs/design-system.md`. Old classes (`stat-card`, `stat-value`, `stat-label`,
  `hover-glow`, `empty-icon-wrapper`) eliminated; no inline `style="color: #hex"` remains except acceptable
  white-on-color icons / `#fbbf24` gold star in QR JS.
- `static/css/style.css` gained ~261 lines of component classes (tokens + badge-soft/btn-outline/btn-danger/
  icon-btn/stat-tile/filter-chip/data-table/list-row/card-header/page-header/action-bar/empty-state).
- All three panels + shared templates render 200 via test client; `pytest -q -n auto` = **169 passed ~30s**;
  `ruff check .` clean; `collectstatic` OK (691 post-processed, manifest storage).
- Commits: `9675c74` (design-system redesign), `f4009de` (SaaS cleanup: flat gradients/glow removal),
  `c8938de` (school_detail clean), `2160174` (remove inline hex on 403 error icons).
- Root templates (`templates/*.html` — login, password reset, 4xx/5xx error pages): verified clean of
  prohibited patterns (no inline `style="color: #hex"`, no gradients/glow). All render OK via
  `render_to_string` (403/403_csrf/404/500/400/login/password_reset).


## Green (verified)
- `python manage.py check` → 0 issues
- `python manage.py collectstatic --noinput --clear` → works, 281 files, hashed names via
  `staticfiles/staticfiles.json` (manifest storage active)
- `python -m pytest -q -n auto --tb=short` → **169 passed in ~29s** (xdist parallel + test-only MD5
  hasher; ~12x faster than the 360s baseline). Use `-n auto` for the fast local run;
  `requirements-dev.txt` includes pytest-xdist.
- `python -m pytest e2e -q --tb=short` → **17 tests total** (14 old + 3 new QR-flow; all pass
  locally on Python 3.12; CI runs on Python 3.13 with Playwright + Postgres)
- `python -m ruff check .` → all passed; `ruff format .` → clean
- **Unified QR**: `/library/my-qr/` generates single STU_ token for student; accessible from my_books tab; `student_qr` view + `student_qr.html` template (redesigned 2026-08-07)
- Smoke render (test client, `HTTP_HOST='localhost'`): `/admin/schools/`, `/admin/schools/<id>/`,
  `/school/books/`, `/school/qr/`, `/profile/` (school_admin) all 200
- **Automated QR flow E2E verified**: static BOOK_/STU_ token gen + QR PNGs (200 image/png),
  scan book→scan student = auto issue, scan again = auto return (available_count tracked),
  student search/pick, clear, state endpoints all green
- **Postgres search path fixed** (2026-08-03): `book_search_vector()` restored in
  `books/models.py`; `books/migrations/0012` GIN index SQL valid + import restored. Compiles to
  `to_tsvector('simple', title || 'A' || author || 'B' || description || 'C')`. Fresh SQLite
  `migrate` from scratch OK; `makemigrations --check` → no changes. This was the CI "Run
  migrations" failure on Postgres (CI red since `3433ecc`).
- **Postgres search path fixed** (2026-08-03): `book_search_vector()` restored in
  `books/models.py`; `books/migrations/0012` GIN index SQL valid + import restored. Compiles to
  `to_tsvector('simple', title || 'A' || author || 'B' || description || 'C')`. Fresh SQLite
  `migrate` from scratch OK; `makemigrations --check` → no changes. This was the CI "Run
  migrations" failure on Postgres (CI red since `3433ecc`).

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
- E2E (`pytest -m e2e`, 14 tests) runs in CI on Python 3.13. Can also run locally (Playwright
  installed, Python 3.12) with `DJANGO_ALLOW_ASYNC_UNSAFE=true` (sqlite in-memory + live_server threads);
  `e2e/conftest.py` guards the Windows asyncio Proactor policy behind `sys.platform == 'win32'`.

## Known gotchas (important)
- URL names are prefixed: `frontend:admin_news_list` / `frontend:school_news_list` /
  `frontend:user_news_list` — never bare `news_list`.
- Import apps as `from <app>.models import ...` (apps/ is on `sys.path`), not `apps.<app>`.
- ruff 0.16.0 formatter can corrupt `except (A, B):` → split into separate `except` clauses.
- Manifest storage fails loudly if a referenced static file is missing (post-processing follows
  references inside CSS/JS) — that's why `chart.umd.min.js` had its sourcemap line removed.
- Test client needs `HTTP_HOST='localhost'` for ALLOWED_HOSTS.

## Recently changed files (this is the "diff to trust")

### 2026-08-06 unified design-system redesign (commit 9675c74)
- `docs/design-system.md` (new — component spec + prohibited patterns)
- `static/css/style.css` (+~261 lines component classes, semantic tokens)
- ALL templates under `apps/frontend/templates/frontend/{admin,school,user,shared}/` (~90 files) — stat-tiles,
  badge-soft, data-table, list-row, unified empty-state, flat buttons

### 2026-08-05 (earlier sessions)
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

### 2026-08-05 security audit + cart rework
- `apps/api/serializers/accounts.py` (read_only: role/school/username, exclude raw_password+password)
- `apps/api/serializers/books.py` (new BookIssuePublicSerializer)
- `apps/api/views/school.py` (HMAC QR, perform_create/update for school enforcement, distribute/collect fixes)
- `apps/api/views/user.py` (textbook ban, categories filter, public serializer, my_rank fix)
- `apps/api/tests.py` (QR/HMAC tests, waitlist test)
- `apps/books/models.py` (BookCart.purpose field, PIL close, Coalesce in search vector)
- `apps/books/migrations/0016_bookcart_purpose.py` (new migration)
- `apps/frontend/views/dispatch.py` (new — profile/password dispatch)
- `apps/frontend/views/user_views.py` (cart rework, month_bounds, N+1 fix, cart_badge)
- `apps/frontend/views/school_views.py` (process_cart_qr, process_cart_return_qr, Category filter, category_id safe parse)
- `apps/frontend/views/admin_views.py` (Category filter, month_bounds)
- `apps/frontend/urls.py` (cart URLs: add/remove/clear/badge/qr/return/*)
- `apps/frontend/templates/frontend/user/cart_*.html` (server-side QR, JSON JS)
- `apps/frontend/templates/frontend/user/sidebar_items.html` (badge JS)
- `apps/frontend/templates/frontend/school/sidebar_items.html` (removed cart link)
- `apps/frontend/templates/frontend/user/book_detail.html` (cart button)
- `apps/frontend/utils.py` (month_bounds helper)
- `docs/agent-context/01-HISTORY.md`, `02-CURRENT-STATE.md`, `03-ROADMAP.md`

### 2026-08-05 admin panel polish + credentials download
- `apps/frontend/templates/frontend/admin/schools.html` (table redesign, no passwords, filters)
- `apps/frontend/templates/frontend/admin/school_detail.html` (password removed, Manzil + issued stat)
- `apps/frontend/views/admin_views.py` (school_count for list; no admin_password for detail)
- `apps/frontend/views/credentials.py` (download by user_id, permission checks)
- `apps/frontend/views/school_views.py` (store raw_password on student/teacher create)
- `apps/frontend/templates/frontend/{admin,school}/*_created.html` (masked password + download button)

### 2026-08-05 school admin profile redesign
- `apps/frontend/templates/frontend/school/profile.html` (hero, 8 stats, quick actions, chart, school info, recent issues)
- `apps/frontend/views/school_views.py` (profile context: available/active/overdue/today + monthly chart)

### 2026-08-05 books page improvements
- `apps/frontend/templates/frontend/school/books.html` (sort, progress bar, live search, QR buttons)
- `apps/frontend/views/school_views.py` (sort param, textbook_count)
- `templates/pagination.html` ({% querystring page=N %} preserves filters)

### 2026-08-05 automated QR issue/return system
- `apps/accounts/utils.py` (generate/verify_static_token for BOOK_/STU_)
- `apps/frontend/views/school_views.py` (qr_book_scanned, qr_student_scanned, _pair_result,
  qr_search_students, qr_pick_student, qr_clear_pending, qr_state, book_qr_image, student_qr_image)
- `apps/frontend/urls.py` (6 new /school/qr/ URLs)
- `apps/frontend/templates/frontend/school/qr_unified.html` (pending panel, student search modal)
- `apps/frontend/templates/frontend/school/books.html` + `student_detail.html` (QR buttons)
- `core/management/commands/seed_demo_data.py` (new — demo categories/books/textbooks/issues/news)
- `docs/agent-context/01-HISTORY.md`, `02-CURRENT-STATE.md`

### 2026-08-05 reader cards, book labels, schools pagination, QR e2e
- `apps/frontend/views/school_views.py` (student_card, book_qr_label, qr_search_students status key)
- `apps/frontend/templates/frontend/school/student_card.html` (new — printable library card)
- `apps/frontend/templates/frontend/school/book_qr_label.html` (new — printable book sticker)
- `apps/frontend/templates/frontend/school/student_detail.html` (Karta button)
- `apps/frontend/templates/frontend/school/books.html` (Yorliq button)
- `apps/frontend/urls.py` (student_card, book_qr_label URLs)
- `apps/frontend/views/admin_views.py` (schools_list: sort + pagination)
- `apps/frontend/templates/frontend/admin/schools.html` (sortable headers, pagination include)
- `e2e/test_qr_flow.py` (new — 3 automated-QR e2e tests)
- `docs/agent-context/01-HISTORY.md`, `02-CURRENT-STATE.md`

### 2026-08-05 school admin tooling — block, reset password, CSV, QR batch, duplicate
- `apps/schools/models.py` (School.is_active field)
- `apps/schools/migrations/0011_historicalschool_is_active_school_is_active.py` (new)
- `apps/accounts/views.py` (login blocks school admins of inactive/deleted schools)
- `apps/frontend/views/admin_views.py` (school_toggle_active, school_reset_admin_password,
  schools_export_csv, school_duplicate)
- `apps/frontend/views/school_views.py` (school_admin_required rejects inactive; qr_labels_batch)
- `apps/frontend/views/admin_views.py` school list/detail templates (block/reset/duplicate buttons,
  status badge, CSV button)
- `apps/frontend/templates/frontend/admin/school_duplicate.html` (new)
- `apps/frontend/templates/frontend/school/qr_labels_batch.html` (new)
- `apps/frontend/templates/frontend/school/sidebar_items.html` (QR yorliqlar link)
- `apps/frontend/urls.py` (toggle-active, reset-admin-password, duplicate, schools/export, labels-batch)
- `docs/agent-context/01-HISTORY.md`, `02-CURRENT-STATE.md`
