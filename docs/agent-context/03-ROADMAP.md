# 03-ROADMAP — What's left / planned

Ordered by priority. Nothing here blocks the current green state; all items are improvements.

## Done (previous sessions)
- ~~Split dev/prod dependencies~~ — done 2026-08-03: `requirements.txt` (prod) + `requirements-dev.txt` (dev); Makefile/tasks.ps1/CI updated.
- ~~Update `docs/CHANGELOG.md`~~ — done: `v1.1.0 (2026-08-03)` covers refactor + modernization.
- ~~Update `README.md` project structure~~ — done (requirements files + `docs/agent-context/`).

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
