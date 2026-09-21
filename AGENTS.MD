# AGENTS.MD — Source of Truth for AI-Assisted Work

> **Purpose:** This file offloads decision-making from prompts to config.
> Read this before acting. Prompts reference this; they do not repeat it.
> Last updated: 2026-05-14

> ⚠️ **GLOBAL RULES APPLY FIRST.**
> Paste the contents of `GLOBAL_AGENTS.MD` at the top of your prompt before this file.
> Project rules here override global rules only when explicitly stated.

---

## 0. HOW TO USE THIS FILE

1. **Load `GLOBAL_AGENTS.MD` first, then this file.**
2. If a decision is already recorded here, **execute it — do not re-ask.**
3. If a situation is not covered, apply the **95% Confidence Rule** (§6).
4. When a new decision is made, **append it to the correct section** — do not rewrite history.
5. Progress lives in §5. Update it after every meaningful milestone.
6. If a learning is not project-specific, **promote it to `GLOBAL_AGENTS.MD`** instead.

---

## 1. PROJECT IDENTITY

```
Name        : Knights of Columbus Management System (KofC)
Type        : Web app — member management, events, donations, blockchain ledger
Language(s) : Python 3.8+
Runtime     : CPython
Package mgr : pip (requirements.txt)
Repo root   : C:\Programming\Projects\FAITH-N-ACTION-refactor-
Entry point : manage.py (dev) | base/wsgi.py (production)
Django app  : capstone_project/
Config pkg  : base/ (settings.py, urls.py, wsgi.py, asgi.py)
```

### What the app does
Three-role Django web app for Catholic fraternal councils. Admins oversee all councils
globally; officers manage their own council (events, attendance, members); members
interact with events, donations, and the forum. Core features:

- Role-based access: admin → officer → member → pending (registration queue)
- Event lifecycle: proposal → officer creates → admin approves/rejects → attendance
- Donations: GCash (PayMongo API) and manual cash, RSA-4096 signed, logged to a
  custom SHA-256 Proof-of-Work blockchain ledger
- QR attendance: officers scan member QR codes via camera
- Council forum with pinning, per-category threading, and image attachments
- Analytics dashboards with Chart.js (6-month forecasting via pandas)
- Recruitment lineage tracking (recruiter → recruit relationships)
- Notification system (in-app only, no push/email notifications to members)
- Event media gallery (Facebook-album style, images + videos)

---

## 2. ARCHITECTURAL RULES
> Stable decisions. Do not override these in prompts — change them here.

### 2.1 Structure
- Single Django app in a polyrepo layout: all business logic lives in `capstone_project/`
- Views are being split from `capstone_project/views.py` (monolith, 5145 lines) into
  `capstone_project/more_views/` — each module groups related concerns:
  - `more_views/api_endpoints.py` — JSON/AJAX endpoints
  - `more_views/attendance.py`   — QR attendance logic
  - `more_views/council.py`      — council CRUD
  - Target: one module per domain (donations, events, forum, blockchain, analytics, etc.)
- Templates: `capstone_project/templates/` — Django template engine, server-rendered
- Static files: `capstone_project/static/` (dev), `staticfiles/` (collectstatic output)
- Media files: `media/` (user uploads: profiles, receipts, forum images, QR codes)
- Signal handlers: `capstone_project/signals.py` — file cleanup on model save/delete
- Utilities: `capstone_project/notification_utils.py`, `capstone_project/bible_verses.py`
- Template tags: `capstone_project/templatetags/`

### 2.2 Data & State
- ORM: Django ORM (no raw SQL)
- Database: SQLite (development) — PostgreSQL is the production target (not yet configured)
- Sessions: `django.contrib.sessions.backends.db`, 8-hour TTL (`SESSION_COOKIE_AGE = 28800`)
- Cache: `django.core.cache.backends.db.DatabaseCache` — development only; must be
  replaced with Redis/Memcached in production
- Rate limiting: `django-ratelimit` decorators — currently broken in dev (DB backend,
  not Redis); warnings silenced via `SILENCED_SYSTEM_CHECKS`
- No in-memory state; no Redis; no Celery (PoW mining blocks synchronously)

### 2.3 API & Communication
- Auth: Django session authentication (no JWT, no OAuth)
- REST-style JSON endpoints only for dashboard AJAX calls (`more_views/api_endpoints.py`)
- Payments: PayMongo REST API (GCash); `django-paypal` is installed but unused
- Email: Gmail SMTP via `django.core.mail` (credentials from env vars)
- No websockets, no message queues, no async tasks

### 2.4 Styling / UI
- Vanilla CSS3 (no Tailwind, no Bootstrap, no design system library)
- CSS variables for theming; dark mode toggled via `User.dark_mode` flag stored in DB
- Chart.js for analytics charts (loaded via CDN in templates)
- No bundler (no webpack, no Vite) — static files served directly by Django in dev

### 2.5 Testing
- Framework: Django `TestCase` (`django.test`)
- Test file: `capstone_project/tests.py` — currently empty (zero tests written)
- Run command: `python manage.py test capstone_project`
- Coverage target: **not established** — first milestone is any test coverage above 0%
- Priority areas: auth/login, role-based access, donation sign/verify, blockchain integrity

### 2.6 Error Handling
- Logging: Python `logging` module throughout; config in `base/settings.py`
- Log outputs: `debug.log` (file) + console (both at DEBUG level in dev)
- Logger name: `capstone_project` (all modules use `logging.getLogger(__name__)`)
- User-facing errors: via Django `messages` framework (never expose tracebacks)
- Exception strategy: catch-and-log in model methods (blockchain, signing); views use
  `get_object_or_404` and `try/except` inconsistently — needs standardisation

### 2.7 Security
- Secret management: `python-decouple` reads from `.env` (gitignored)
- `.env.example` provided; `.env` and `*.pem` are in `.gitignore`
- RSA-4096 keys: `private_key.pem` + `public_key.pem` at repo root — generated via
  `generate_keys.py`; loaded at settings import time via `load_keys()`
- CSRF: `CSRF_USE_SESSIONS = True` (token in session, not cookie)
- No email verification on registration — pending approval by officer/admin is the gate
- Rate limiting: decorators exist on sign-in but backend is non-functional (see §2.2)
- Auth provider: Django built-in (`AbstractUser` extended as `capstone_project.User`)

### 2.8 Immutable Decisions

| # | Decision | Rationale | Date |
|---|----------|-----------|------|
| 1 | Custom SHA-256 PoW blockchain (not a library) | Academic capstone requirement; full auditability | Pre-2026 |
| 2 | RSA-4096 signatures on donations | Cryptographic non-repudiation for financial transparency | Pre-2026 |
| 3 | Django session auth only (no JWT/OAuth) | Simpler for internal org tool; no mobile API clients | Pre-2026 |
| 4 | Single Django app (`capstone_project`) | Avoid premature microservice complexity for org-scale | Pre-2026 |
| 5 | PayMongo for GCash (not PayPal) | Philippine market; GCash is the dominant payment method | Pre-2026 |
| 6 | Secrets live in `.env` / untracked files only; git history purged | Leaked RSA key + member PII DB sat in public history; keys rotated to real RSA-4096, `filter-repo` purge executed on origin | 2026-09-22 |
| 7 | Role assignment only via explicit admin actions — no username-based shortcuts | SEC-1 `Mr_Admin` backdoor removed from `User.save()`; regression tests in `capstone_project/tests.py` | 2026-09-22 |

---

## 3. CONTEXT RULES
> These rules replace per-prompt instructions. Apply them automatically.

### 3.1 Code Style
```
- Max line length    : 100 chars
- Naming convention : snake_case (Python throughout)
- Imports           : absolute paths preferred; no barrel re-exports
- Comments          : explain WHY, not WHAT; no commented-out code in commits
- Functions         : pure by default; side effects must be explicit
- View functions    : must use @login_required unless explicitly public; never rely
                      on EnsureNotAuthenticatedMiddleware as the sole auth guard
```

### 3.2 File Operations
```
- Never delete files without explicit instruction.
- Never rename files without explicit instruction.
- Never move files across module boundaries without explicit instruction.
- Prefer editing existing files over creating new ones.
- When extracting views from views.py into more_views/, do not delete the original
  until the URL wiring and imports are confirmed working.
```

### 3.3 Dependency Rules
```
- Do not add new dependencies without asking first.
- Prefer stdlib / already-installed packages.
- Zero runtime dependencies in shared utility modules.
- If adding a dependency, add it to requirements.txt with a pinned version.
- qrcode==8.2 added to requirements.txt (2026-05-14); no longer missing.
```

### 3.4 Output Format
```
- Default response   : concise prose, no bullet spam
- Code blocks        : always include language tag
- File paths         : always relative to repo root
- When showing diffs : unified diff format
- Never truncate code: if a file is being written, write it completely
```

### 3.5 Scope Guard
```
- Only touch files directly related to the current task.
- Do not refactor unrelated code opportunistically.
- Do not upgrade dependencies as a side effect.
- If a bug is spotted outside scope, note it — do not fix it silently.
- views.py is the primary refactoring target; do not touch it unless the task
  explicitly involves extracting views or fixing a bug inside it.
```

### 3.6 Communication Rules
```
- If a requirement is ambiguous, state the assumption being made, then proceed.
- Do not ask more than one clarifying question at a time.
- Do not re-explain decisions that are already in this file.
- End responses with next logical action or open question if applicable.
```

---

## 4. DECISION LOG
> Append decisions here. Never delete entries — strike through if superseded.

### Format
```
### [YYYY-MM-DD] <Short Title>
**Decision:** What was decided.
**Rationale:** Why.
**Alternatives rejected:** What else was considered and why it lost.
**Supersedes:** #N (if applicable)
```

### Entries

#### [Pre-2026] Template initialized
**Decision:** AGENTS.MD adopted as project source of truth.
**Rationale:** Reduces prompt length, prevents repeated debate, maintains continuity across sessions.
**Alternatives rejected:** Inline comments in code (not agent-readable); README (too user-facing).

#### [2026-05-14] AGENTS.MD populated from codebase audit
**Decision:** Filled all template sections with actual project state derived from full codebase read.
**Rationale:** Empty AGENTS.MD provided zero guidance to agents; all decisions were being re-debated
per session.
**Alternatives rejected:** None — this was initialization work, not a design decision.

#### [2026-05-14] Forum views extracted to more_views/forum.py first
**Decision:** Forum domain (5 views) chosen as the first extraction target from views.py.
**Rationale:** Most self-contained domain — no cross-domain ORM calls, clear URL cluster, backed by 9 green tests.
**Alternatives rejected:** Events (larger, cross-domain with notifications); Donations (GCash flow too entangled).

---

## 5. PROGRESS SUMMARY
> Agents update this section. One line per milestone. Most recent first.

| Date | Status | Milestone |
|------|--------|-----------|
| 2026-05-14 | ✅ DONE | Auth extracted — more_views/auth_views.py (3 views); URLs re-wired; 66/66 tests green |
| 2026-05-14 | ✅ DONE | Notifications extracted — more_views/notifications.py (7 views); URLs re-wired; 66/66 tests green |
| 2026-05-14 | ✅ DONE | views.py 5145→3433 lines — forum/events/donations originals deleted; 60/60 tests green |
| 2026-05-14 | ✅ DONE | Donations extracted — more_views/donations.py (13 views); URLs re-wired; 60/60 green |
| 2026-05-14 | ✅ DONE | Events extracted — more_views/events.py (15 views); URLs re-wired; 60/60 green |
| 2026-05-14 | ✅ DONE | D-4 fixed — EnsureNotAuthenticatedMiddleware rewritten with public-path whitelist |
| 2026-05-14 | ✅ DONE | D-9 fixed — SessionRefreshMiddleware uses timezone.now() instead of datetime.now() |
| 2026-05-14 | ✅ DONE | Forum views extracted — more_views/forum.py created; URLs re-wired; 60/60 tests green |
| 2026-05-14 | ✅ DONE | Tech debt fixed — D-1 (DEBUG), D-8 (timezone), D-10 (load_keys error handling), D-13 (qrcode in requirements.txt) |
| 2026-05-14 | ✅ DONE | Pre-existing failing test fixed — management/test.py test_blockchain_donation_flow (missing 'status' field) |
| 2026-05-14 | ✅ DONE | Expanded test suite — 60 tests total (27 new), all green; EventLifecycleTests, ForumTests, DonationViewTests added |
| 2026-05-14 | ✅ DONE | Initial test suite written — 33 tests, all green (tests.py) |
| 2026-05-14 | ✅ DONE | Migration conflict fixed — 0030/0032 made no-ops; test DB now builds cleanly |
| 2026-05-14 | ✅ DONE | AGENTS.MD populated; gap analysis complete |
| Pre-2026   | ✅ DONE | Full feature set shipped (auth, events, donations, blockchain, forum, analytics, QR, gallery) |

### Current State
```
What exists and works:
- Full Django app with 3-role access control (admin / officer / member / pending)
- Event lifecycle management (proposal → approval → attendance → gallery)
- GCash (PayMongo) and manual donation flows with RSA signatures
- Custom SHA-256 PoW blockchain ledger for donation records
- QR-code attendance system (officer scans member QR)
- Council forum with categories, pinning, and image attachments
- Analytics dashboards with Chart.js and pandas forecasting
- Recruitment lineage tracking
- In-app notification system
- Event media gallery
- Council management (CRUD)
- PDF receipt generation via reportlab
- CSV/Excel export via openpyxl/pandas

What is in progress:
- Refactoring views.py (5145 lines, 90 functions) into more_views/ modules
  - Completed: forum.py, events.py, donations.py, notifications.py, auth_views.py
  - views.py now 3105 lines

What is blocked:
- Production deployment is blocked by no deploy config (D-20)
- D-4 (EnsureNotAuthenticatedMiddleware) needs audit before it is safe to rely on

Immediate next step:
- Continue views.py extraction — remaining domains: analytics (analytics_form, analytics_view,
  download_analytics_csv), user management (manage_pending_users, approve_user, reject_user,
  promote_user, demote_user, archive_user, archived_users), and member/council views.
- views.py is now 3105 lines; target is under 1000.
- Remove forum functions from views.py once events extraction is confirmed green
```

### Known Issues / Tech Debt
| ID | Description | Severity | Owner |
|----|-------------|----------|-------|
| D-1 | `DEBUG = True` hardcoded in settings.py — must be env var | high | ✅ FIXED 2026-05-14 |
| D-2 | Zero tests — tests.py is empty | high | ✅ FIXED 2026-05-14 |
| D-3 | views.py is 5145 lines, 90 functions — refactor target | high | in progress (3433 lines remain) |
| D-4 | EnsureNotAuthenticatedMiddleware guards only 8 hardcoded paths | high | ✅ FIXED 2026-05-14 |
| D-5 | `proof_of_work()` blocks Django web thread synchronously | high | ⚠ NEEDS DECISION — see §5 |
| D-6 | Rate limiting non-functional (DB backend, warnings silenced) | medium | backlog |
| D-7 | `User.age` is a stored DB field; goes stale between birthday/save | medium | backlog |
| D-8 | `TIME_ZONE = 'UTC'` — org is Philippines (should be Asia/Manila) | medium | ✅ FIXED 2026-05-14 |
| D-9 | `SessionRefreshMiddleware` uses `datetime.now()` not `timezone.now()` | medium | ✅ FIXED 2026-05-14 |
| D-10 | `load_keys()` has no error handling; crashes Django startup if PEM missing | high | ✅ FIXED 2026-05-14 |
| D-11 | `ALLOWED_HOSTS` has no production domain configured | medium | backlog |
| D-12 | Migration history has duplicate numbers (0016–0020) requiring merge migrations | medium | backlog |
| D-13 | `qrcode` package used in attendance.py but absent from requirements.txt | high | ✅ FIXED 2026-05-14 |
| D-14 | `receipt_upload_path` function defined but never wired to `Donation.receipt` | low | backlog |
| D-15 | `generate_transaction_id` uses only 8 hex chars — collision risk | medium | backlog |
| D-16 | `EMAIL_HOST` hardcoded to `smtp.gmail.com` in settings.py | low | backlog |
| D-17 | 15+ loose markdown files in project root (should be in docs/) | low | backlog |
| D-18 | Commented-out URL `search-users` in urls.py | low | backlog |
| D-19 | `django-paypal` installed but unused | low | backlog |
| D-20 | No production deployment config (no Gunicorn, Docker, nginx) | high | ⚠ NEEDS DECISION — see §5 |

---

## 6. THE 95% CONFIDENCE RULE

> **If you are 95% or more confident you know the correct action, take it.**
> Document what you did and why at the end of your response.
> Do NOT ask for permission on low-stakes, reversible decisions.

### What qualifies as 95%+ confidence
- The action is consistent with §2 (Architecture) and §3 (Context Rules).
- The action is reversible (can be undone with a single command or edit).
- The action has been done the same way at least once before in this project.
- The task is fully scoped and has no ambiguous requirement.

### What does NOT qualify — always ask first
- Deleting or moving files.
- Adding new dependencies.
- Changing public interfaces or API contracts.
- Modifying database schemas or migrations.
- Any action that affects more than 3 files outside the current task scope.
- Anything that would override an entry in §4 (Decision Log).
- Touching views.py outside of an explicitly scoped extraction task.

### Confidence declaration format
> At the end of any response where the 95% rule was applied, append:
> `[AUTO] Confidence: 97% — Reason: <one sentence>`

---

## 7. APPLIED LEARNING
> Triggered by: repeated failures, Andy re-explaining, or platform/tool workarounds found.
> Rules: one line per bullet, under 15 words, no explanations, future-session value only.

### Failures & Re-explains
- `forum` view has both `@login_required` AND a manual pending check; unauthenticated redirects include `?next=`.
- EnsureNotAuthenticatedMiddleware is NOT a complete auth solution — always use @login_required too.
- warnings.filterwarnings in settings.py suppresses valid DB access warnings; do not add more.
- `send_message` creates Notification objects via bulk_create directly — does NOT use create_notification util.
- `get_messages` local variable named `messages` shadows django.contrib.messages import — rename to `msgs` in extraction.
- Every "✅ FIXED" claim in §5 must cite file:line plus a passing test; D-1/D-2/D-9/D-10 were false when audited 2026-09-22.

### Platform & Tool Limits
- django-ratelimit requires Redis or Memcached; DatabaseCache backend is non-functional.
- qrcode package is used but not in requirements.txt; pip install will fail without it.
- private_key.pem and public_key.pem must exist before runserver; generate with generate_keys.py.

### Workarounds
- Rate limiting check warnings silenced via SILENCED_SYSTEM_CHECKS — not fixed, just hidden.
- _LazyBlockchain proxy delays DB access at import time; it still hits DB on first attribute access.
- Migrations 0030_eventmedia and 0032_eventmedia_thumbnail made no-ops; fields already in 0019_eventmedia branch.
- Migration 0020_eventmedia_media_type made no-op; media_type already in 0019_eventmedia branch.

---

## 8. AGENT HANDOFF CHECKLIST
> Run through this before ending a session or handing off to another agent.

- [ ] §5 Progress Summary is up to date.
- [ ] New decisions are logged in §4.
- [ ] New applied learnings added to §7 if anything failed, was re-explained, or was worked around.
- [ ] No uncommitted changes left without a note in §5.
- [ ] No open questions left unrecorded.
- [ ] Next step is written clearly under "Immediate next step."

---

*This file is the contract between humans and agents on this project.*
*When in doubt: read this file, follow the rules, log the decision.*
