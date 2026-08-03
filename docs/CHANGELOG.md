# Changelog

## v1.1.0 (2026-08-03)

### Added
- Soft delete for API resources (`SoftDeleteManager`, `SoftDeleteMixin`) — migrations `accounts/0012`, `books/0014`, `schools/0010`
- Audit history via `django-simple-history` (`HistoricalRecords`) on key models
- Shared sidebar (`frontend/shared/sidebar_items.html`) used by all three panels
- `frontend:profile_edit` URL for the existing `profile_edit` view
- `requirements-dev.txt` — prod (`requirements.txt`) vs dev/test/lint tooling split

### Changed
- Reworked `apps/frontend/urls.py` — all patterns under `app_name = 'frontend'`
- Added `__all__` to `api/views/__init__.py` and `api/serializers/__init__.py`
- Static pipeline: `django-compressor` removed → whitenoise `CompressedManifestStaticFilesStorage`; `{% compress %}` stripped from templates; `?v=` cache-busters removed
- Database driver: `psycopg2-binary` → `psycopg[binary]` (v3)
- `pyproject.toml`: `core` added to pytest `testpaths` (was silently skipped); stale per-file-ignores removed
- AGENTS.md now points agents to `docs/agent-context/` (state/history/roadmap)
- CI/Makefile/tasks.ps1 install `requirements-dev.txt`

### Fixed
- `frontend/admin/profile.html` missing `{% load frontend_tags %}` (500 on admin profile page)
- `static/js/chart.umd.min.js` broken `sourceMappingURL` reference (failed manifest post-processing)

### Removed
- `gunicorn` (unused — `start.sh` runs only daphne)
- `django-compressor`, `rcssmin`

## v1.0.0 (2026-07-04)

### Added
- Initial release of Online Kutibxona library management system
- QR-based book borrowing/returning with HMAC dynamic tokens
- Three roles: Super Admin, School Admin (Librarian), Student/Teacher
- Gamification: XP points, levels, achievements, challenges, streaks
- Grade promotion: auto-promotes on Sept 1, graduates archived
- Multi-language: Uzbek, Russian, English, Karakalpak
- Glassmorphism UI with light/dark theme and responsive design
- Charts: monthly usage stats, category distribution (Chart.js 4.4.1)
- Push notifications (Web Push API + VAPID)
- Brute-force protection (django-axes)

### Security
- Removed plaintext password storage (`raw_password`)
- Fixed missing authentication decorator on `student_edit` view
- Changed `DEBUG` default to `False`
- Improved `SECRET_KEY` handling with proper fallback
- Enabled django-axes brute-force protection (5 attempts, 1h lockout)
- Added password reset flow with email templates
- Fixed XSS via `|safe` filter (replaced with `|escapejs`)
- Added `robots.txt` to block admin panels from search engines

### Fixed
- Challenges template bug: progress never displayed (dictsort → get_item filter)
- Missing 403 error handler in URL configuration
- Duplicate validator functions consolidated into `core/validators.py`
- `generate_password()` now uses `secrets.choice()` instead of `random`

### Added
- CSV import for students and books (school admin panel)
- Pagination on library book catalog (24 per page)
- Search/filter on admin schools, all_books, active_loans list views
- Logging configuration (console + file)
- SVG favicon
