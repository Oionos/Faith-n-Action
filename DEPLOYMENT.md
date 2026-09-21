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

Current baseline: **25 tests, 0 failures, 0 errors, 5 expected failures.**
Expected failures are deliberate — each documents a confirmed defect in
`views.py` that requires owner approval to fix (AGENTS.MD §6):

| Test | Defect | Fix needed |
|---|---|---|
| `test_member_cannot_read_other_members_full_details` | SEC-5 IDOR — member reads any member's PII | scope `user_details` by role |
| `test_anonymous_update_degree_is_rejected_not_500` | SEC-8 duplicate `update_degree` def lost `@login_required` | delete one duplicate (views.py:874 vs 2151) |
| `test_anonymous_member_list_rejected_not_500` | `member_list` (views.py:1968) lacks `@login_required` | add decorator |
| `test_amount_mismatch_does_not_complete_donation` | SEC-6 payment amount never verified | compare source amount to donation amount |
| `test_completed_donation_cannot_be_reconfirmed` | Http404 falls into broad `except` -> UnboundLocalError -> 500 | catch Http404 before the generic handler |

When a fix lands, the test flips to *unexpected success* — remove the
`@unittest.expectedFailure` decorator and keep the test as a permanent guard.

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

Requires approving and installing `requirements-prod.txt` first (G2 rule).

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
- [ ] `python manage.py test` green (expected failures resolved or accepted)
- [ ] SEC-5, SEC-6, SEC-8, member_list fixes applied (views.py — needs owner approval)
- [ ] `SECRET_KEY` rotated (post-breach), `DEBUG=False` verified on the host
- [ ] New RSA-4096 keys generated on the host; PEMs mounted as secrets, never in the image
- [ ] Existing pre-rotation donation signatures marked legacy (see security.md SEC-2)
- [ ] Stress baseline recorded and acceptable for expected council load
- [ ] `requirements-prod.txt` approved and installed
