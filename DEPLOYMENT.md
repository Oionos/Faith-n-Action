# Faith-n-Action — Deployment & Testing Guide

## Prerequisites

```powershell
pip install -r requirements.txt
python generate_keys.py            # creates private_key.pem / public_key.pem (RSA-4096, git-ignored)
copy .env.example .env             # then fill in real values
python manage.py migrate
python manage.py createsuperuser   # then set role='admin' via admin panel or shell
```

## Running the test suite

```powershell
python manage.py test              # full suite (built-in runner, no extra deps)
python manage.py test capstone_project.tests.test_security      # one module
python manage.py test capstone_project.tests.test_permissions.PermissionMatrixTests
```

Current baseline: **27 tests, 0 failures, 0 errors — no expected failures.**
Coverage (`coverage run --source=capstone_project manage.py test`): **51% total**,
`models.py` 81%, `views.py` 35%. The formerly expected-failing tests were guards
for defects fixed 2026-09-22 — they now run as permanent regression guards:

| Guard | Defect (fixed) |
|---|---|
| `test_member_cannot_read_other_members_full_details` | SEC-5 IDOR — `user_details` scoped by role |
| `test_anonymous_update_degree_is_rejected_not_500` | SEC-8 duplicate `update_degree` removed, decorators restored |
| `test_anonymous_member_list_rejected_not_500` | `member_list` gained `@login_required` |
| `test_anonymous_council_members_rejected_not_500` | `council_members` gained `@login_required` |
| `test_amount_mismatch_does_not_complete_donation` | SEC-6 PayMongo amount verified (centavos) |
| `test_completed_donation_cannot_be_reconfirmed` | Http404 re-raised, no more UnboundLocalError 500 |

Known remaining gaps (next targets): registration POST flow (sign-up view),
event lifecycle views, forum send/delete/pin, file-upload validation.

## Stress testing

```powershell
python manage.py runserver          # terminal 1
python scripts/stress_test.py --requests 200 --concurrency 10          # terminal 2
python scripts/stress_test.py --scenario signin --requests 100 --concurrency 5
```

The harness is stdlib-only and CSRF-aware. Watch for `database is locked`
errors — that is the SQLite writer-lock ceiling (PERF-3). Sustained
production load requires PostgreSQL (see requirements-prod.txt).

## Production deployment (Docker)

`requirements-prod.txt` is approved and installed (gunicorn, whitenoise,
psycopg, django-ratelimit, coverage). Note: gunicorn runs in the Docker
image (Linux); locust is omitted on Windows — see the file's note.

```powershell
docker compose up --build -d        # gunicorn behind nginx (deploy/nginx.conf)
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Production `.env` must set: `DEBUG=False`, `ALLOWED_HOSTS=yourdomain.com`,
`SECURE_SSL_REDIRECT=True`, `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`,
`SECURE_HSTS_SECONDS=31536000`, `BEHIND_TLS_PROXY=True`, a fresh `SECRET_KEY`,
and real PayMongo/SendGrid keys.

## Pre-go-live checklist

- [ ] `python manage.py check --deploy` clean
- [ ] `python manage.py test` green (27 tests) — keep it green
- [ ] Postgres provisioned and `DATABASE_URL` set (SQLite default is dev-parity only)
- [ ] SEC-5, SEC-6, SEC-8, member_list fixes applied (views.py — needs owner approval)
- [ ] `SECRET_KEY` rotated (post-breach), `DEBUG=False` verified on the host
- [ ] New RSA-4096 keys generated on the host; PEMs mounted as secrets, never in the image
- [ ] Existing pre-rotation donation signatures marked legacy (see security.md SEC-2)
- [ ] Stress baseline recorded and acceptable for expected council load
- [ ] `requirements-prod.txt` approved and installed
