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

Current baseline: **95 tests, 0 failures, 0 errors, 0 expected failures.**
Coverage (`coverage run --source=capstone_project manage.py test`): **69% total**,
`models.py` 82%, `views.py` 57%.

Sign-up hardening (2026-09-22, all guarded by tests):
- E-signature uploads are **decode-validated** via a shared
  `_validate_uploaded_image()` helper — the client-supplied `content_type` is no
  longer trusted; format comes from Pillow, with a 40 MP decompression-bomb cap.
- `AUTH_PASSWORD_VALIDATORS` now run on **both** sign-up and `edit_profile`
  (previously bypassed, so `password='123'` was accepted).
- `edit_profile` profile-picture writes (base64 `cropped_image`) are
  decode-validated too — this previously raised `UnidentifiedImageError` → HTTP 500.

Guards in place (all passing):

| Guard | Defect (fixed) |
|---|---|
| `test_member_cannot_read_other_members_full_details` | SEC-5 IDOR — `user_details` scoped by role |
| `test_anonymous_update_degree_is_rejected_not_500` | SEC-8 duplicate `update_degree` removed, decorators restored |
| `test_anonymous_member_list_rejected_not_500` | `member_list` gained `@login_required` |
| `test_anonymous_council_members_rejected_not_500` | `council_members` gained `@login_required` |
| `test_amount_mismatch_does_not_complete_donation` | SEC-6 PayMongo amount verified (centavos) |
| `test_completed_donation_cannot_be_reconfirmed` | Http404 re-raised, no more UnboundLocalError 500 |
| `test_officer_batch_marks_attendance` | batch attendance 500 — dead `Activity` import removed |
| `test_e_signature_content_type_spoof_rejected` | SEC-14 — uploads decode-validated, not header-trusted |
| `test_weak_password_rejected` / `test_password_similar_to_username_rejected` | password validators enforced on sign-up |
| `test_weak_password_change_rejected` / `test_invalid_cropped_image_rejected` | same enforcement in `edit_profile` |
| `test_title_only_notification_does_not_crash` | `get_notifications` AttributeError on `message=None` (degree-change rows) fixed |
| `test_admin_adds_manual_recruitment_and_degree_recalculates` | recruitment create + `recalculate_degree` promotion side-effects verified |
| `test_cannot_mark_another_users_notification` | `mark_notification_read` scoped to owner (404) |
| `test_officer_cannot_move_member_from_another_council` | `change_council` officer scope guard |

Notification wiring gap (2026-09-22): `get_notifications` and
`mark_notification_read` have **no URL routes** in either URLconf, and
`base.html`'s "notification" container is the Django messages toast system —
so `Notification` rows written by `send_message` and `recalculate_degree`
are never displayed anywhere. The views are tested directly via
RequestFactory (`test_notifications.py`). Decision needed: wire the routes
(feature add) or remove the dead views.

Known remaining gaps (next targets): GCash initiate/confirm views, council
CRUD, QR attendance scanning, event media gallery, CSV/PDF exports,
`manage_roles`, `manage_pending_users`.

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
- [ ] `python manage.py test` green (95 tests) — keep it green
- [ ] Postgres provisioned and `DATABASE_URL` set (SQLite default is dev-parity only)
- [ ] SEC-5, SEC-6, SEC-8, member_list fixes applied (views.py — needs owner approval)
- [ ] `SECRET_KEY` rotated (post-breach), `DEBUG=False` verified on the host
- [ ] New RSA-4096 keys generated on the host; PEMs mounted as secrets, never in the image
- [ ] Existing pre-rotation donation signatures marked legacy (see security.md SEC-2)
- [ ] Stress baseline recorded and acceptable for expected council load
- [ ] `requirements-prod.txt` approved and installed
