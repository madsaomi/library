# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please report it by emailing the project maintainer.
Do **not** create a public GitHub issue.

## Security Features

- **CSRF protection** on all forms
- **CORS headers** configurable via env vars
- **Brute-force protection**: 5 failed login attempts → 1 hour lockout (django-axes)
- **Role-based access**: `user_passes_test` for all admin/school_admin views
- **Password hashing**: PBKDF2/SHA256 (Django default)
- **No plaintext password storage**: passwords displayed once at creation, never persisted
- **HMAC-signed QR tokens**: 120-second time window, constant-time comparison
- **HTTPS enforcement**: configurable via `SECURE_COOKIES` env var
- **Session security**: SameSite=Lax, configurable for production
