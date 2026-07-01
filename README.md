# Online Kutibxona

Smart library management system for schools with QR-code, gamification (XP, levels, achievements), and multi-language support.

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
- **Glassmorphism UI**: light/dark theme, responsive
- **Charts**: monthly stats, category distribution (Chart.js)

## Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.13, Django 5.0 |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Cache | LocMemCache (dev) / Redis (prod) |
| Frontend | Vanilla JS, CSS3, Chart.js |
| QR | html5-qrcode + HMAC tokens |
| Admin | Jazzmin |

## Quick start

```bash
git clone <repo> && cd library
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Structure

```
library/
├── core/              # Settings, middleware, URLs
├── accounts/          # Users, roles, auth
├── schools/           # Schools, districts, institutions
├── books/             # Catalog, issues, requests, achievements
├── stats/             # Action logs
├── notifications/     # Push subscriptions, in-app notifications
├── frontend_admin/    # Super admin panel
├── frontend_school/   # School admin panel
├── frontend_user/     # Student/teacher panel
├── static/            # CSS, JS
├── templates/         # Base layouts
└── locale/            # Translations (.po / .mo)
```

## Security

- **CSRF** protection, `CORS` headers
- **Password validators**, change form
- **Rate limiting** on login: 5 failures → 1h block (axes)
- **Role-based access**: `user_passes_test` for admin/school_admin
- **Session** security configurable via env vars
- No raw SQL, no `mark_safe`

## Cache

Default: local memory. For Redis:

```bash
CACHE_BACKEND=django_redis.cache.RedisCache
CACHE_LOCATION=redis://...
```

## Translations

```bash
python -c "import polib; [polib.pofile(f'locale/{l}/LC_MESSAGES/django.po').save_as_mofile(f'locale/{l}/LC_MESSAGES/django.mo') for l in ['uz','ru','en','kaa']]"
```

## License

MIT
