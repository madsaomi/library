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

## Session: fix e2e login root cause (2026-08-04)
- **Root cause of e2e failures (CI red since e2e were added)**: e2e/conftest.py created the test
  superuser dmin in a **session-scoped** `django_db_setup` override. pytest-django runs
  `live_server` tests inside `TransactionTestCase` (`transactional_db` is auto-requested), and
  `TransactionTestCase` **flushes the whole DB after every test** — so after the first e2e test the
  admin user was gone. Every subsequent `login` fixture timed out waiting for `**/admin/**` and
  AXES logged "New login failure". Reproduced locally: `ADMIN USER COUNT: 0` in the second test.
- **Fix**: moved user creation to a **function-scoped** `transactional_db` override
  (documented pytest-django pattern for data visible to `live_server`). Admin is (re)created at the
  start of every e2e test and cleaned up by the flush. Verified locally: all **14 e2e tests pass**,
  all **168 unit tests pass**, `ruff check` clean.
- Also removed the unused `from django.core.management import call_command` import from
  `e2e/conftest.py`; kept the `sys.platform == 'win32'` asyncio Proactor policy guard (local-only,
  inert on Linux CI).

## Session: clean up minor issues in modules (2026-08-04)
- **pps/books/achievements.py**: LEVEL_TABLE + fallback had hardcoded Russian level titles
  ('Новичок'…'Легенда') — project default language is uz. Replaced with Uzbek names wrapped in
  gettext_lazy so they can be translated if locale files are added later.
- **pps/books/models.py**: Book.save() caught image-optimization errors with a bare
  print(...) — silently lost from logging. Swapped to logger.warning(...) (added
  logging.getLogger(__name__)).
- **core/middleware.py**: GradePromotionMiddleware had an unreachable
  except IndexError: continue after parts[0] — already guarded by if not student.grade /
  parts[0] index access. Removed the dead clause.
- **pps/books/tests.py**: Updated 	est_get_level_info to assert 'Boshlang\'ich' instead of
  'Новичок' (reflects the i18n change).
- **Verified**: 168 unit tests green; uff check clean.


## Session: deeper logic review — school/user views (2026-08-04)
- **pps/frontend/views/school_views.py** dashboard: removed dead or request.user.is_superuser
  clause in the news filter. The view is already decorated with @school_admin_required (checks
  ole == 'school_admin' and school is not None), so a superuser could never reach this code path.
- **pps/frontend/views/user_views.py** library + 
ews_list: added early guard for
  equest.user.school is None. Previously a user without a school (e.g. a newly-created teacher)
  would silently see an empty library or empty news list instead of an error message. Now redirects
  to /login/ with a clear Uzbek error.
- **Verified**: 168 unit tests green; uff check clean.


## Session: deeper API + permissions review (2026-08-04)
- **pps/api/permissions.py**: IsStudent, IsTeacher, IsStudentOrTeacher did NOT check
  school is not None, unlike IsSchoolAdmin. Users without a school would reach views that
  access equest.user.school and silently get empty results instead of being rejected.
  Added nd request.user.school is not None to all three.
- **pps/api/views/user.py** CatalogViewSet.get_queryset: added guard
  if not self.request.user.school: return Book.objects.none() — prevents querying without a
  school.
- **pps/api/views/user.py** CatalogViewSet.reader_of_month: fixed two bugs —
  (a) removed dead except ReaderOfMonth.DoesNotExist (.first() never raises it),
  (b) don't cache None for 3600s (only cache when a reader is found).
- **pps/api/views/user.py** BookDetailViewSet.reserve: was auto-approving
  (status='approved') which bypassed the school admin approval flow. Changed to create a
  status='pending' request (matching the frontend eserve_book behavior). Also skips
  creating a duplicate request if one already exists.
- **pps/api/tests.py**: updated 	est_catalog_reader_of_month to also verify None is
  returned when no reader is set (the fix now doesn't crash).


## Session: cart system + sidebar improvements (2026-08-04)
- **pps/books/models.py**: Added BookCart and BookCartItem models with soft delete.
  BookCart tracks student book selections with QR token and status (pending/borrowed/returned).
- **pps/frontend/views/user_views.py**: Implemented cart flow:
  - cart_list — show selected books
  - cart_add/remove/clear — manage items
  - cart_generate_qr — generate single QR for all books
  - cart_borrow_confirm — school admin confirms borrowing
  - cart_return_list/add/qr/confirm — return flow
- **pps/frontend/urls.py**: Added 13 cart-related URLs under /library/cart/...
- **pps/frontend/templates/frontend/{school,user}/sidebar_items.html**: Added
  **prominent cart button** with badge showing item count, styled with gradient background
  for visibility. Works for both school admin and student roles.
- **pps/books/admin.py**: Registered models for admin panel.
- **Migration**:  015_bookcart_bookcartitem.py created and applied.


## Session: security audit + cart rework (2026-08-05)
- **Critical security fixes (escalation of privilege)**:
  - `CustomUserSerializer` (`apps/api/serializers/accounts.py`): `role`, `school`, `username`
    now `read_only` - students could previously PATCH their own `role` to `superuser`
    (`update_profile` applies `serializer.save()` directly to `request.user`).
  - `SchoolStudentViewSet` / `SchoolTeacherViewSet` (`apps/api/views/school.py`): added
    `perform_update` forcing `school=request.user.school` + `role` (school admin could previously
    raise a created user's role to `superuser` via PUT). Added `is_deleted=False` to querysets.
  - `CustomUserDetailSerializer`: `fields='__all__'` -> `exclude=['raw_password', 'password']`
    (raw passwords were being serialized to API clients).
- **Caching**: removed `@cache_page(60*5)` from admin and school `dashboard` (personalized/cross-school
  data leak - one school's dashboard could be served to another admin).
- **API QR flow rewritten** (`apps/api/views/school.py` `QrProcessView`): now uses the same HMAC
  rotating tokens as the frontend (`REQ_<id>_<hash>` / `RET_<id>_<hash>` via `verify_dynamic_token`),
  `transaction.atomic` + `select_for_update` for `available_count`, textbook ban for students,
  `award_xp(user, 'borrow'/'return')` with correct args, `ActionLog` entries.
- **`award_xp` call sites fixed**: `QrProcessView.issue` `award_xp(..., 10)` ->
  `award_xp(user, 'borrow', book=...)`; `return_book` `award_xp(..., 5)` -> `award_xp(user, 'return')`.
- **Cross-school writes blocked**: `SchoolIssueViewSet`, `TextbookLoanViewSet`, `SchoolBookViewSet`
  now validate `book`/`user`/`student` belong to the admin's school in `perform_create`/`perform_update`.
- **TextbookLoan**: `distribute` now requires `due_date` + uses `select_for_update`/`transaction.atomic`
  with `F()` decrement; `collect` only matches loans with `returned_at__isnull=True` (was double-returning).
- **API user fixes** (`apps/api/views/user.py`): `reserve` blocks textbooks for students and blocks
  when the user already has an active copy; `join_waitlist` blocks when copies are available;
  `categories` filters `is_deleted=False`; `active_reads` now uses new `BookIssuePublicSerializer`
  (no QR tokens leaked); `my_rank` is now a single count query instead of looping.
- **Cart rework (was broken)**:
  - `BookCart.purpose` field added (`borrow`/`return`) + migration `0016`; borrow and return carts
    are now separate (`CART_*` vs `RETCART_*` tokens).
  - `cart_remove`/`cart_clear`/`cart_return_remove`/`cart_return_clear` now return JSON (the JS
    expects `{success:true}`); `cart_clear` fixed `hard_delete` bug; removed dead/broken
    `cart_borrow_confirm`/`cart_return_confirm` views + URLs.
  - QR pages now generate the PNG server-side (`generate_qr_code`), replacing the broken client-side
    qrcodejs fetch/modal that never rendered. `cart_generate_qr`/`cart_return_qr` return a page that
    the JS opens in a new window.
  - School scanner (`process_qr_unified`) now handles `CART_*`/`RETCART_*`: `process_cart_qr`
    issues books atomically (textbook ban, availability, XP, notification, ActionLog);
    `process_cart_return_qr` returns them (XP, completes request, notifies next waitlist).
  - `cart_return_list` shows active issues with "add to return cart" buttons; `cart_add` blocks
    textbooks for students; added `cart_badge` JSON endpoint + sidebar badge JS; removed cart link
    from the school sidebar (student-only feature).
- **Profile routing** (`apps/frontend/views/dispatch.py`): `frontend:profile` / `frontend:change_password`
  are now role-aware dispatchers - school admins/students no longer get bounced to login by
  `@superuser_required`.
- **Misc**: Postgres search uses `Coalesce` (books with NULL author no longer crash search);
  `month_bounds()` helper in `apps/frontend/utils.py` fixes calendar-month chart math in
  `user_views.profile` + admin dashboard; `my_class` N+1 eliminated via `annotate`;
  `category_id` parsing hardened; PIL `Image`/buffer closed in `Book.save`; `Category.objects`
  filtered by `is_deleted=False` in library/school/admin lists.
- **Verification**: `manage.py check` 0 issues; `ruff check .` + `ruff format .` clean;
  **168 unit tests PASS**; e2e 13/14 on Windows (1 CDN timeout flake, stable in CI).

## Session: remaining audit fixes (2026-08-05)
- **M1**: CSV import APIs now return `credentials: [{username, password}]` for each imported student
- **L6**: Removed duplicate `GraduateViewSet`; kept `SchoolStudentViewSet.graduates` action
- **M5**: `check_achievements` bulk-fetches earned IDs + pre-computes all aggregates in 2 queries (was O(N×2))
- **M8**: `WaitlistSerializer.get_position` uses `Window(RowNumber())` (single query, no N+1)
- **L9**: `update_streak` now counts consecutive days (delta==1 → +1 streak) instead of ISO weeks
- **L10**: `Book.save()` enforces `0 <= available_count <= total_count` for plain int values
- **L11**: Removed `unique=True` from `BookCart.qr_token` (prevents race-condition unique violations)
- **L12**: `SuperUserStatsView.list` filters `is_deleted=False` on all model queries
- **Tests**: 169 passed (+1 new streak test), ruff clean

## Session: auto-generate school admin credentials (2026-08-05)
- **school_add view**: auto-generates admin_username (admin_{school_name}_{random_hex}) and
  admin_password (14-char random string) when fields are left empty
- **New template school_created.html**: shows credentials with copy-to-clipboard and
  toggle-password buttons, warns user to save securely
- **Python**: 169 tests PASS, ruff clean

## Session: admin panel polish (2026-08-05)
- **Schools list** (`schools.html`): redesigned from cards to a table (like `all_users.html`) —
  stat row (schools/students/books/districts), server + client search, district filter dropdown,
  admin column with eye-toggle password (later removed), action icons; view passes `school_count`.
- **School detail** (`school_detail.html`): removed password + eye toggle, added "Manzil" card and
  "Tarqatilgan kitoblar" (issued) stat; removed unused `admin_password` from view context.
- **Passwords removed everywhere in admin UI**: `schools.html` list no longer shows admin passwords;
  only usernames. Downloads moved to secure endpoint (see below).
- **Credential download** (`credentials.py`): `download_credentials` rewritten to take `user_id`
  (looks up `raw_password` from DB instead of passing it through the URL), permission checks
  (superuser or same-school school_admin). Views now store `raw_password` on create for
  student/teacher/admin too. All four `*_created.html` pages show a masked password + a
  "Parolni yuklab olish" button (no more on-screen password/eye toggle).

## Session: school admin profile redesign (2026-08-05)
- **`school/profile.html`** fully rewritten: gradient hero card (avatar, name, role, school,
  district, change-password button), 4 quick-action dashed buttons (add student/teacher, manage
  books, QR scanner), 8 stat cards (students/teachers/books/copies/active issues/overdue/issued
  today/returned today — clickable), monthly activity bar chart (Chart.js), school info block
  (district/contact/address), recent issues table, recent activity feed.
- **`school_views.profile`**: added `available_copies`, `active_issues`, `overdue_issues`
  (>30 days unreturned), `issued_today`/`returned_today`, `recent_issues`, monthly chart data.

## Session: books page improvements (2026-08-05)
- **`school/books.html`**: added 5th stat (textbook count), sort dropdown (title A-Z/Z-A, most
  read, availability, newest), availability progress bar on each card, borrow-count number next to
  stars, live client-side search (title/author/category), click-on-card opens edit, accent "Yangi
  kitob" button, QR button per card.
- **`school_views.books_list`**: added `sort` param + `textbook_count`.
- **`templates/pagination.html`**: rewritten to use Django 5.1+ `{% querystring page=N %}` so all
  GET filters (q/sort/category/textbook) survive page navigation (previously only `q` did).

## Session: automated QR issue/return system (2026-08-05)
- **Static HMAC tokens** (`accounts/utils.py`): `generate_static_token(prefix, id)` /
  `verify_static_token(token, prefix)` → `BOOK_<id>_<hash>` and `STU_<id>_<hash>` (no expiry, for
  printed labels).
- **Auto issue/return pairing** (`school_views.py`): scanning a `BOOK_` then a `STU_` token (either
  order) auto-decides: if the student already holds the book → auto-return, else auto-issue
  (availability check, textbook ban for students, XP award, notification, ActionLog, waitlist
  notify on return). Session stores `qr_pending_book_id` / `qr_pending_student_id`.
- **New views**: `qr_book_scanned`, `qr_student_scanned`, `qr_search_students` (JSON),
  `qr_pick_student`, `qr_clear_pending`, `qr_state`, `book_qr_image` / `student_qr_image`
  (PNG generated on the fly). New URLs under `/school/qr/`.
- **`qr_unified.html`**: pending-pairing panel ("Jarayon" showing book + student), handles `info`
  responses, "O'quvchini qidirish" modal with debounced JSON search, clear/reset button,
  auto-refresh state on load.
- **QR buttons**: green QR button on every book card (`book_qr_image`) + QR button in student
  detail hero (`student_qr_image`) — open printable PNG in new tab.
- **`seed_demo_data` command** (`core/management/commands/seed_demo_data.py`): creates 7 categories,
  32 regular books (Uzbek classics), 5 textbooks, 12 book issues, 3 news per school; idempotent
  via get_or_create; `--school-id` / `--force` flags. Ran for school "1 1-sonli maktab" (id 5).
- **Verified**: 169 unit tests PASS, ruff clean, `manage.py check` 0, full E2E scan flow
  (book→student issue, book→student return, student search/pick, clear, state) all green.

## Session: reader cards, book labels, schools pagination, QR e2e (2026-08-05)
- **Reader card** (`student_card` view + `student_card.html`): printable library card for a
  student — credit-card size, gradient, name/grade/school/ID + static STU_ QR image, print button
  (window.print with print CSS). URL `/school/students/<pk>/card/`; "Karta" button in student
  detail hero.
- **Book QR label** (`book_qr_label` view + `book_qr_label.html`): printable white sticker —
  title/author/category/ID + BOOK_ QR, textbook badge; print button. URL
  `/school/qr/book-label/<pk>/`; tag button added next to QR on book cards.
- **Schools list pagination + sorting** (`schools_list`): `sort` param
  (name/district/students/books, ±), `Paginator(…, 20)`, `page_obj` + `page_obj` in context;
  table headers are now clickable sort links using `{% querystring sort=… %}`; added pagination
  include. Sort toggle helper computed in view.
- **e2e tests** (`e2e/test_qr_flow.py`, 3 tests): `test_qr_auto_issue_and_return` (scan book→
  student = issue, scan again = return via `/school/qr/process-unified/`), `test_qr_student_search`
  (JSON search), `test_qr_image_endpoints` (book/student QR PNGs 200 + image/png). Added
  `status:'success'` to `qr_search_students` response.
- **CI/Postgres**: new views use standard ORM only (no Postgres-specific SQL); removed a dead
  `django.contrib.postgres.search` import from `qr_search_students`. Docker not available locally,
  so Postgres path is verified by CI (`DATABASE_URL` Postgres in tests.yml).
- **Verified**: 169 unit tests PASS; 3 new e2e tests PASS locally (total 17 e2e); ruff clean;
  `manage.py check` 0; schools sorts + card + label all render 200.

## Session: school admin tooling — block, reset password, CSV, QR batch, duplicate (2026-08-05)
- **School blocking**: `School.is_active` field (default True) + migration `schools/0011`; login
  blocked in `accounts/views.py` login_view for school admins of inactive/deleted schools;
  `school_admin_required` decorator also rejects inactive schools (kicks out already-logged-in
  admins). Toggle view `school_toggle_active` + "Bloklash/Faollashtirish" button + status badge on
  school detail + list.
- **Reset admin password**: `school_reset_admin_password` view — random 14-char password, stored in
  `raw_password`, shown once in a success message ("Parolni almashtirish" button on school detail).
- **CSV export**: `schools_export_csv` view (`/admin/schools/export/`) — ID/name/district/address/
  contact/admin/students/books/status; "CSV" button in schools list toolbar.
- **QR batch print**: `qr_labels_batch` view + `qr_labels_batch.html` (`/school/qr/labels-batch/`)
  — grid of all book or student QR stickers (4-per-row in print), toggle kind (books/students),
  print button; sidebar "QR yorliqlar" link.
- **Duplicate school**: `school_duplicate` view + `school_duplicate.html` — POST copies
  address/contact/district under a new name (auto-suffixed if taken), generates fresh admin
  username + password (raw_password saved), no books/students; "Nusxa" button on school detail.
- **Verified**: 169 unit tests PASS; ruff clean; `manage.py check` 0; E2E smoke — block/login-reject/
  re-enable, reset password (raw_password set), CSV 200 text/csv, duplicate creates school+admin,
  QR batch renders 38 book + 2 student labels.

## Session: minimal student panel redesign (2026-08-05)
- **`user-panel` body class**: base.html adds it for student/teacher roles; `static/css/style.css`
  gains a "STUDENT MODE" block — flat cards (no heavy shadow/glow), subtle rounded pills
  (`.pill-subtle`, `.pill-available`, `.pill-unavailable`), quiet stat tiles (`.user-stat`),
  clean section titles (`.user-section-title`), calmer sidebar + nav-link.
- **Catalog** (`library.html`): removed news ticker animation, "So'nggi faoliyat" log feed, and
  reader-of-month banner; now a clean grid with one compact news strip, search + category chips
  (`.filter-chip`), muted availability pills instead of 3-count stat boxes / star ratings.
- **Sidebar** (`sidebar_items.html`): removed search box, replaced gradient cart button with calm
  `.sidebar-cart-link`, clearer 3 sections (Asosiy / Faoliyat / Ma'lumot).
- **my_books**: dropped loud XP badges (10 XP/5 XP) and neon colors; consistent empty states.
- **profile / achievements**: no purple gradients or glow, flat XP bar, `user-stat` tiles.
- **leaderboard**: table → quiet `.leader-row` list with rank medals + `.is-me` highlight.
- **challenges / my_class / news / book_detail / cart_list / cart_return_list**: consistent
  minimal styling, removed `btn-danger`, `badge bg-success`, bold colored icons.
- **Verified**: 169 unit tests + 17 e2e PASS; all student pages render 200; ruff clean.

## Session: dynamic backgrounds & glassmorphism polish for auth and error pages (2026-08-05)
- **Dynamic background system** (`static/css/style.css`): `.auth-bg-layer`, `.error-bg-layer`, `.bg-orb` (`bg-orb-1`, `bg-orb-2`, `bg-orb-3`), `.dynamic-canvas`, `.error-watermark`, `.auth-card-premium`, `.error-card-premium`. Keyframe animations for floating orbs, mesh pulse, and icon badges. Fully theme-aware (`dark`, `light`, `autumn`, `winter`).
- **Auth pages** (`login.html`, `password_reset.html`, `password_reset_confirm.html`, `password_reset_done.html`, `password_reset_complete.html`): interactive Canvas particle system, glowing gradient background orbs, glassmorphic card, input icon indicators, smooth theme & language controls.
- **Error pages** (`404.html`, `500.html`, `403.html`, `400.html`, `403_csrf.html`, `axes_lockout.html`): customized background orb colors, watermark text ("404", "500", "403", "CSRF", "400", "LOCKED"), error icon badges, particle background, theme switch button.
- **Verified**: `python manage.py collectstatic --noinput` (691 static files post-processed), `python -m pytest -q -n auto --tb=short` (169 passed in ~35s), `python -m ruff check .` (clean).

## Session: SaaS design cleanup — flat, calm, 2 themes (2026-08-06)
- **Flat background**: removed radial-gradient orbs from `body`; now plain `--bg-dark` (Linear-style).
- **Reduced themes 4 → 2**: removed `[data-theme="autumn"]` and `[data-theme="winter"]` blocks from
  `style.css`; updated `cycleTheme()` in `base.html` + auth/error pages (`login.html`, `400.html`,
  `403.html`, `403_csrf.html`, `404.html`, `500.html`, `axes_lockout.html`) to only cycle
  `dark <-> light` with `fa-moon`/`fa-sun` icons.
- **Flat avatars**: replaced all `linear-gradient(135deg, var(--primary), #a855f7)` avatar/icon
  circles with plain `var(--primary)` (profile, achievements, sidebar).
- **No emojis**: swapped leaderboard 🥇🥈🥉 for FA icons `fa-crown`/`fa-medal`; offline page 📚 → `fa-wifi`.
- **Verified**: all 10 student pages render 200; 169 unit tests PASS; ruff clean.





## Session: unified design system applied across all ~90 templates (2026-08-06)
- **Design-system spec** written at `docs/design-system.md`: card containers (`glass-panel`/`glass-card`),
  `stat-tile` grid, `btn-primary/btn-outline/btn-danger`, `icon-btn`, `badge-soft-*`, semantic text
  colors (`text-success/warning/danger/info/muted`), `filter-chip`, unified `empty-state` + `empty-icon`,
  `data-table` in `.table-responsive-wrap`, `list-row` family, `page-header`/`action-bar`/`card-header`.
  Prohibited: linear-gradient, glow box-shadows, inline `style="color: #hex"`, old classes (`stat-card`,
  `stat-value`, `stat-label`, `hover-glow`, `empty-icon-wrapper`, `text-4xl text-primary` in empties).
- **New CSS** appended to `static/css/style.css` (~261 lines): `--success/--warning/--danger/--info` tokens
  (dark + light overrides) and the component classes above.
- **All admin templates** (24), **school templates** (32), **user templates** (18), **shared password_change**
  converted to the new system: stat-tiles, badge-soft statuses, data-tables, list-rows, unified empty-states,
  flat action buttons. Old `stat-card/stat-value/stat-label` eliminated everywhere.
- **Spot fixes** after scan: `school/profile.html` rewritten (hero + 8 stat-tiles + quick actions + chart +
  school info + recent issues as data-table, Chart.js via `json_script`), `school/qr_unified.html` stat-tiles,
  `school/qr_labels_batch.html` empty-state, `student_form`/`teacher_form` label colors, `user/issue_qr` +
  `user/request_qr` success headings/borders to tokens, `shared/password_change.html` gradient removed.
- **Verified**: all panel pages render 200 (test client, HTTP_HOST=localhost); `pytest -q -n auto` = **169
  passed in ~30s**; `ruff check` clean; `collectstatic` OK (691 post-processed).
- Committed + pushed: `9675c74` "refactor: redesign all panel templates to unified design system".

## Session: final verification across all templates + root (2026-08-06)
- Verified root auth/error templates (login, password_reset, 400/403/404/500/403_csrf) render
  without errors after removing last inline hex colors on 403 icons.
- Ran full test suite: **169 passed**, ruff clean, collectstatic OK.
- Updated docs/agent-context/ files to reflect current state.
- No further template work needed � design-system applied uniformly.

## Session: admin panel polish (2026-08-06)
- **admin_edit.html** � rewritten with card-header, section titles with icons, password visibility toggle
  (	ogglePassword() JS), cleaner form layout. Credentials section highlighted with warning border.
- **admin_created.html** � improved success card with icon badge, password toggle on displayed password,
  cleaner credentials card layout, improved visual hierarchy.
- **all_users.html** � cleaned up action-bar (search with icon, proper filter-chips), removed inline
  padding styles, consistent badge-soft usage.
- **user_detail.html** � added row-actions (edit button for school_admin), stat-tiles with icons,
  info-grid with card-header, activity history as list-row instead of old activity-item.
- **statistics.html** � cleaned action-bar (period select with proper label), consistent stat-tiles,
  card-headers on all panels.
- Verified: 169 tests pass, ruff clean, all pages render 200.
- Commit: 4e85c8f "refactor: improve admin pages - all_users, user_detail, statistics"

## Session: user panel polish (2026-08-06)
- **achievements.html** � uses .progress-bar/.progress-fill for progress display, card-header for section titles
- **challenges.html** � uses .progress-bar/.progress-fill, unified empty-state with description
- **leaderboard.html** � card-header for ranking section, uses list-row for ranked students, improved podium layout
- **library.html** � uses .password-wrapper for search input with icon, card-header for news link, consistent empty-states
- **my_books.html** � improved empty-states with descriptions, consistent list-row usage
- Verified: all user pages render 200, 169 tests pass, ruff clean
- Commit: 11ae0f5 "refactor: improve user panel templates with design system"
