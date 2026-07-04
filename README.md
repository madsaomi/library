# Online Kutibxona

Smart library management system for schools with QR-code borrowing, gamification (XP, levels, achievements, streaks), multi-language support, and glassmorphism UI.

![Python](https://img.shields.io/badge/python-3.13%2B-blue)
![Django](https://img.shields.io/badge/django-5.0-green)
![License](https://img.shields.io/badge/license-MIT-gray)

## Features

- **QR-based** borrowing/returning (HMAC dynamic tokens, refresh every 2 min)
- **3 roles**: Super Admin, School Admin (Librarian), Student/Teacher
- **Gamification**: XP points, levels, achievements, challenges, streaks
- **Grade promotion**: auto-promotes students on Sept 1, graduates archived
- **Brute-force protection**: django-axes (5 attempts → 1h lockout)
- **Notifications**: bell dropdown + push notifications + top banner
- **Multi-language**: Uzbek, Russian, English, Karakalpak
- **Glassmorphism UI**: light/dark theme, responsive (400px–1600px)
- **Charts**: monthly stats, category distribution (Chart.js 4.4.1)
- **CSV import/export**: students, books, issues

## Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.13+, Django 6.0 |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Cache | LocMemCache (dev) / Redis (prod) |
| Frontend | Vanilla JS, CSS3, HTMX 2.x, Chart.js 4.4.1 |
| QR | html5-qrcode + HMAC-SHA256 tokens |
| Admin | Jazzmin |
| CI | GitHub Actions (pytest) |

## Quick Start

```bash
git clone <repo> && cd library
python -m venv venv && source venv/bin/activate  # venv\Scripts\activate on Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Demo Credentials

| Role | Login | Password |
|------|-------|----------|
| Super Admin | `superadmin` | `admin123` |
| School Admin | `admin{school_id}` | `admin123` |
| Student | `student{school_id}_{n}` | `student123` |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | — | Django secret key (**required in production**) |
| `DEBUG` | `False` | Debug mode |
| `DATABASE_URL` | SQLite | PostgreSQL connection string |
| `CACHE_BACKEND` | `LocMemCache` | Redis: `django_redis.cache.RedisCache` |
| `CACHE_LOCATION` | — | Redis URL |
| `EMAIL_BACKEND` | `console` | SMTP: `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` | — | SMTP host |
| `EMAIL_HOST_USER` | — | SMTP user |
| `EMAIL_HOST_PASSWORD` | — | SMTP password |
| `VAPID_PUBLIC_KEY` | — | Web Push public key |
| `VAPID_PRIVATE_KEY` | — | Web Push private key |

## Tests

```bash
pytest -v
```

## Translations

```bash
python -c "import polib; [polib.pofile(f'locale/{l}/LC_MESSAGES/django.po').save_as_mofile(f'locale/{l}/LC_MESSAGES/django.mo') for l in ['uz','ru','en','kaa']]"
```

## Deployment

### Docker

```bash
docker-compose up --build
```

### Railway

Deploy from GitHub. Set required env vars (`SECRET_KEY`, `DATABASE_URL`).

## Project Structure

```
library/
├── core/              # Settings, middleware, URLs, validators
├── accounts/          # Users, roles, auth, utils
├── schools/           # Schools, districts, institutions
├── books/             # Catalog, issues, requests, achievements
├── stats/             # Action logs, management commands
├── notifications/     # Push subscriptions, in-app notifications
├── frontend_admin/    # Super admin panel (dashboard, schools, stats)
├── frontend_school/   # School admin panel (students, books, QR, CSV)
├── frontend_user/     # Student/teacher panel (library, profile, challenges)
├── static/            # CSS, JS, favicon
├── templates/         # Base layouts, auth pages
├── locale/            # Translations (.po / .mo)
├── scripts/           # Schedule scripts (daily, weekly, monthly)
└── .github/           # CI workflow
```

## Security

- CSRF protection, CORS headers
- Password hashing (no plaintext storage)
- Brute-force protection (django-axes)
- Role-based access (`user_passes_test`)
- HMAC-signed QR tokens with 120s expiry
- Configurable HTTPS enforcement

## License

MIT
