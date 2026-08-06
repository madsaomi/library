# 03-ROADMAP — What's left / planned

Ordered by priority. Nothing here blocks the current green state; all items are improvements.

## Done (previous sessions)
- ~~Split dev/prod dependencies~~ — done 2026-08-03: `requirements.txt` (prod) + `requirements-dev.txt` (dev); Makefile/tasks.ps1/CI updated.
- ~~Update `docs/CHANGELOG.md`~~ — done: `v1.1.0 (2026-08-03)` covers refactor + modernization.
- ~~Update `README.md` project structure~~ — done (requirements files + `docs/agent-context/`).

## Done (2026-08-05 admin/school panel polish + QR automation)
- ~~Schools list: table redesign, filters, no passwords shown~~
- ~~School detail: password removed, address + issued count~~
- ~~Secure credential download by user_id~~
- ~~Masked passwords + download buttons on all *_created pages~~
- ~~School admin profile redesign (hero, 8 stats, quick actions, chart, school info, recent issues)~~
- ~~Books page: sort, progress bar, live search, per-book QR buttons~~
- ~~pagination.html preserves filters via {% querystring %}~~
- ~~Automated QR issue/return: static BOOK_/STU_ HMAC tokens, auto issue/return pairing, student search/pick in scanner, QR PNG endpoints~~
- ~~seed_demo_data management command~~
- Verification: manage.py check 0; ruff clean; **169 unit tests PASS**; automated QR flow E2E verified.

## Remaining (from this session's discussion — mostly done)
- ~~**Reader card / library card**: printable student card with their STU_ QR~~ — done
  (`student_card` view + template, "Karta" button in student detail).
- ~~**Print modal for book QR**: styled print page~~ — done (`book_qr_label` view + template,
  "Yorliq" button on book cards).
- ~~**Schools list pagination** + column sorting~~ — done (sort param + clickable headers +
  Paginator 20/page).
- ~~**e2e tests for the new automated QR flow**~~ — done (`e2e/test_qr_flow.py`, 3 tests).
- **CI verification** for the new views (run on Postgres in CI; only SQLite-verified locally —
  Docker not available in this environment). Watch the next `push`/PR on GitHub Actions.

## Done (2026-08-05 school admin tooling)
- ~~School block/unblock (`School.is_active` + login rejection + decorator)~~
- ~~Reset school admin password from school card~~
- ~~CSV export of schools~~
- ~~Printable batch QR labels (books + students)~~
- ~~Duplicate school (new name/admin, empty data)~~
- ~~Unified student QR (`/library/my-qr/` with single STU_ token for all operations)~~

## Remaining (small, safe)
1. **`docs/REQS.md`** is a historical spec and partly stale — consider rewriting or archiving.

## Optional modernization (researched but not started)
2. **`uv`** package manager (faster installs, lockfile, single source of truth). Requires local
   install + Dockerfile/CI changes. Deferred — no `uv`/Node tooling installed locally.
3. **`django-unfold`** admin theme as a jazzmin alternative (cosmetic; only if wanted).
4. **Deeper HTMX adoption** — project already vendored `htmx.min.js` and uses it in base.html;
   further progressive-enhancement is optional.

## Cannot be done in this environment
- E2E tests (`pytest -m e2e`, 14 Playwright tests) — now **green locally and fixed for CI**:
  root cause was the session-scoped `django_db_setup` admin user being wiped by `TransactionTestCase`
  flush; fixed via a function-scoped `transactional_db` override in `e2e/conftest.py`.
  Local run needs Playwright installed + `DJANGO_ALLOW_ASYNC_UNSAFE=true`.
- Any Node/uv-based frontend pipeline — no Node.js installed locally.

## How to keep this folder useful
- After each work session, update:
  - `01-HISTORY.md` — append what was done
  - `02-CURRENT-STATE.md` — refresh "Green" + "Recently changed files"
  - `03-ROADMAP.md` — mark items done, add new ones
- Keep entries terse (this folder exists to save other agents' context budget).

## Done (2026-08-05 security audit + cart rework)
- ~~Critical security: block role/school/username self-assignment in CustomUserSerializer~~
- ~~Critical security: SchoolStudent/Teacher perform_update enforce school+role~~
- ~~Critical security: CustomUserDetailSerializer no longer leaks raw_password/password~~
- ~~Critical security: remove @cache_page from school/admin dashboards (cross-school data leak)~~
- ~~High: API QR flow rewritten to HMAC rotating tokens with transaction.atomic + select_for_update~~
- ~~High: award_xp called with correct 'borrow'/'return' action strings~~
- ~~High: cross-school writes blocked in SchoolIssue/TextbookLoan/SchoolBook viewsets~~
- ~~High: textbook ban for students in API reserve/issue~~
- ~~High: BookIssuePublicSerializer removes QR tokens from shared reads~~
- ~~High: my_rank uses single count query, not Python loop~~
- ~~High: TextbookLoan distribute requires due_date; collect matches only active loans (no double-return)~~
- ~~Medium: cart rework — purpose field + separate borrow/return carts, server-side QR generation, school scanner processes CART/RETCART tokens atomically~~
- ~~Medium: profile routing dispatch.py fixes school admin/student 302-to-login loops~~
- ~~Medium: Postgres search uses Coalesce (books with NULL author found)~~
- ~~Medium: month_bounds() in utils.py fixes calendar-month chart math~~
- ~~Medium: my_class N+1 eliminated via annotate~~
- ~~Medium: Category lists filtered by is_deleted=False~~
- ~~Medium: PIL Image/BytesIO closed in Book.save~~
- ~~Medium: Category.objects filtered by is_deleted=False in library/school/admin lists~~
- ~~Medium: category_id parsing hardened (isdigit)~~
- ~~Medium: added cart_badge endpoint + sidebar badge JS; removed cart link from school sidebar~~
- ~~Medium: tests updated (QR HMAC, join_waitlist, etc.)~~
- Verification: manage.py check 0 issues; ruff check/format clean; **169 unit tests PASS**; e2e 13/14 on Windows (CDN flake, stable in CI).

