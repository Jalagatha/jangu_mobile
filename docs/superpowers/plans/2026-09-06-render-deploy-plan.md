# Render Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the `jango_mobileapp` Django backend deployable on Render's free tier from a committed `render.yaml` blueprint, with no paid add-ons and no pre-provisioned database.

**Architecture:** Additive, backwards-compatible changes. `settings.py` switches to a `DATABASE_URL`-driven database (SQLite fallback), serves static files with WhiteNoise, and trusts Render's injected hostname. A `render.yaml` blueprint defines one free web service that builds, collects static, migrates, and bootstraps a superuser from env vars on each deploy. Postgres and S3-compatible media are pre-wired and activate via env vars only.

**Tech Stack:** Django 5.2, gunicorn, WhiteNoise, dj-database-url, psycopg 3, django-storages + boto3 (dormant), Render Blueprint (`render.yaml`).

**Spec:** `docs/superpowers/specs/2026-09-06-render-deploy-design.md`

**Deviations from spec (intentional, discovered during planning):**
- `SECURE_SSL_REDIRECT` defaults to **False** (not True). Render's edge already forces HTTPS; a Django-level redirect risks a double redirect that can fail health checks. Still overridable via env var.
- Superuser bootstrap is a dedicated idempotent management command `accounts.ensure_superuser` (not a raw `createsuperuser --no-input || true`), because the custom user model needs phone normalization/validation and a clean no-op path.
- `mysqlclient` is already broken in the local venv (dylib load failure) and `manage.py test` cannot run against MySQL locally today. The SQLite default fixes local dev as a side effect; the post-change test run is the real regression gate.

---

## File Structure

| File | Create/Modify | Responsibility |
| --- | --- | --- |
| `requirements.txt` | Modify | Add deploy deps (`gunicorn`, `whitenoise`, `dj-database-url`, `psycopg`, `django-storages`, `boto3`); remove `mysqlclient`. |
| `backend/backend/settings.py` | Modify | `DATABASE_URL` database, WhiteNoise static storage, Render host/CSRF trust, opt-in S3 media, production security toggles. |
| `backend/accounts/management/__init__.py` | Create | Package marker. |
| `backend/accounts/management/commands/__init__.py` | Create | Package marker. |
| `backend/accounts/management/commands/ensure_superuser.py` | Create | Idempotently create a superuser from `DJANGO_SUPERUSER_*` env vars; no-op when unset or already present. |
| `backend/accounts/tests/test_ensure_superuser.py` | Create | Tests for the command. |
| `render.yaml` | Create | Blueprint: one free web service, build/start commands, env var declarations. |
| `backend/.env.example` | Modify | Document `DATABASE_URL`, `CSRF_TRUSTED_ORIGINS`, `USE_S3`, drop `DB_*`. |
| `backend/.env.production` | Delete | Committed secret; Render config lives in the dashboard/blueprint. |
| `.gitignore` | Modify | Ignore `.env.*` except `.env.example`. |
| `DEPLOY-RENDER.md` | Create | Operator runbook: first deploy, env vars, admin user, DB/media upgrades, troubleshooting. |

`backend/passenger_wsgi.py` is left untouched — the Namecheap/cPanel deploy stays as a fallback.

---

## Task 1: Feature branch

**Files:** none (git only)

- [ ] **Step 1: Create the branch**

Run:
```bash
cd /Users/mac/projects/jango_mobileapp
git switch -c deploy/render
```
Expected: `Switched to a new branch 'deploy/render'`

- [ ] **Step 2: Confirm clean tree on the new branch**

Run: `git status`
Expected: `nothing to commit, working tree clean` (the spec/plan docs are already committed on `main` and carried over).

---

## Task 2: Deployment dependencies in `requirements.txt`

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Replace the file contents**

Write `requirements.txt` (repo root) exactly as:

```
asgiref==3.11.1
attrs==26.1.0
boto3==1.43.89
botocore==1.43.89
brotli==1.2.0
dj-database-url==3.1.2
Django==5.2.15
django-cors-headers==4.9.0
django-environ==0.11.2
django-extensions==3.2.3
django-filter==24.3
django-storages==1.14.6
djangorestframework==3.15.2
djangorestframework-simplejwt==5.3.1
drf-spectacular==0.27.2
gunicorn==26.2.0
inflection==0.5.1
jmespath==1.1.0
jsonschema==4.26.0
jsonschema-specifications==2025.9.1
pillow==10.4.0
psycopg==3.3.5
psycopg-binary==3.3.5
pydot==3.0.2
PyJWT==2.13.0
python-dateutil==2.9.0.post0
PyYAML==6.0.3
referencing==0.37.0
rpds-py==2026.6.3
s3transfer==0.19.2
six==1.17.0
sqlparse==0.5.5
uritemplate==4.2.0
urllib3==2.7.0
whitenoise==6.12.0
```

Changes vs. current: removed `mysqlclient==2.2.8`; added `boto3`, `botocore`, `brotli`, `dj-database-url`, `django-storages`, `gunicorn`, `jmespath`, `psycopg`, `psycopg-binary`, `python-dateutil`, `s3transfer`, `six`, `urllib3`, `whitenoise`.

- [ ] **Step 2: Install into the local venv**

Run:
```bash
cd /Users/mac/projects/jango_mobileapp
source .venv/bin/activate
pip install -r requirements.txt
```
Expected: ends with `Successfully installed ... dj-database-url-3.1.2 ... gunicorn-26.2.0 ... psycopg-3.3.5 ... whitenoise-6.12.0` and no `ERROR`.

- [ ] **Step 3: Verify the new imports resolve**

Run:
```bash
python -c "import dj_database_url, whitenoise, storages, boto3, gunicorn; print('ok')"
```
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
cd /Users/mac/projects/jango_mobileapp
git add requirements.txt
git commit -m "build: add Render deploy deps, drop mysqlclient"
```

---

## Task 3: Make `settings.py` deployment-ready

**Files:**
- Modify: `backend/backend/settings.py`

All edits are additive. Local dev keeps reading `backend/.env`.

- [ ] **Step 1: Update the import block**

Replace:
```python
"""Django settings for the Jango Mobile backend project."""

from pathlib import Path

import environ
from datetime import timedelta
```
with:
```python
"""Django settings for the Jango Mobile backend project."""

import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
import environ
```

- [ ] **Step 2: Trust Render's hostname for ALLOWED_HOSTS / CSRF**

Replace:
```python
SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])
```
with:
```python
SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# Render injects the service's public hostname at runtime. Trust it so the
# app works on the *.onrender.com URL before any custom domain is configured.
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")
```

- [ ] **Step 3: Add WhiteNoise middleware**

Replace:
```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
```
with:
```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
```

- [ ] **Step 4: Replace the MySQL DATABASES block**

Replace:
```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST", default="127.0.0.1"),
        "PORT": env("DB_PORT", default="3306"),
        "OPTIONS": {"charset": "utf8mb4"},
    }
}
```
with:
```python
# DATABASE_URL drives the database. Unset -> local SQLite file (used for dev
# and Render's free tier). Set to a postgres:// URL -> Postgres with no code
# change (psycopg ships in requirements.txt).
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}
```

- [ ] **Step 5: Add static file storage + opt-in S3 media**

Replace:
```python
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```
with:
```python
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
            if not DEBUG
            else "django.contrib.staticfiles.storage.StaticFilesStorage"
        ),
    },
}

# Opt-in S3-compatible media storage (AWS S3 / Cloudflare R2 / Backblaze B2).
# Dormant until USE_S3=true; activates via env vars alone, no code change.
USE_S3 = env.bool("USE_S3", default=False)
if USE_S3:
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default=None)
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default=None)
    AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN", default=None)
    AWS_QUERYSTRING_AUTH = env.bool("AWS_QUERYSTRING_AUTH", default=False)
    AWS_DEFAULT_ACL = None
    STORAGES["default"]["BACKEND"] = "storages.backends.s3.S3Storage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

- [ ] **Step 6: Add production security toggles at end of file**

Replace the final line:
```python
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
```
with:
```python
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

# Production hardening (only when DEBUG is false). Render terminates TLS at
# its edge and forwards X-Forwarded-Proto, and already redirects http->https
# there, so SECURE_SSL_REDIRECT stays off by default to avoid a double
# redirect that can trip health checks. Override via env var if needed.
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
```

- [ ] **Step 7: System check passes**

Run:
```bash
cd /Users/mac/projects/jango_mobileapp/backend
source ../.venv/bin/activate
python manage.py check
```
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 8: Full test suite passes on the SQLite default**

Run:
```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py test
```
Expected: `OK` (all tests pass). The test DB is in-memory SQLite. `Address.save()`'s `select_for_update()` is a silent no-op on SQLite — `test_new_default_unsets_previous_default` still passes because the `is_default` bookkeeping runs inside the same `transaction.atomic()` block.

If any test fails, STOP and diagnose before continuing.

- [ ] **Step 9: Deploy check shows only the expected warnings**

Run:
```bash
DJANGO_SETTINGS_MODULE=backend.settings DEBUG=False SECRET_KEY=dummy python manage.py check --deploy
```
Expected: warnings only, no errors. `security.W004` (HSTS) and `security.W008` (SSL redirect) are expected and intentional (documented in the spec). No `?: (ERROR ...)` lines.

- [ ] **Step 10: Commit**

```bash
cd /Users/mac/projects/jango_mobileapp
git add backend/backend/settings.py
git commit -m "feat: make settings deployable on Render (DATABASE_URL, WhiteNoise, host trust)"
```

---

## Task 4: `ensure_superuser` management command (TDD)

**Files:**
- Create: `backend/accounts/management/__init__.py`
- Create: `backend/accounts/management/commands/__init__.py`
- Create: `backend/accounts/management/commands/ensure_superuser.py`
- Test: `backend/accounts/tests/test_ensure_superuser.py`

- [ ] **Step 1: Create the package markers**

Create `backend/accounts/management/__init__.py` — empty file.
Create `backend/accounts/management/commands/__init__.py` — empty file.

- [ ] **Step 2: Write the failing test**

Create `backend/accounts/tests/test_ensure_superuser.py`:

```python
import os
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from accounts.models import User

ENV = {
    "DJANGO_SUPERUSER_PHONE": "0771234567",
    "DJANGO_SUPERUSER_PASSWORD": "strongpass123",
    "DJANGO_SUPERUSER_FIRST_NAME": "Ada",
    "DJANGO_SUPERUSER_LAST_NAME": "Lovelace",
}


class EnsureSuperuserCommandTests(TestCase):
    def test_skips_when_env_missing(self):
        out = StringIO()
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DJANGO_SUPERUSER_PHONE", None)
            os.environ.pop("DJANGO_SUPERUSER_PASSWORD", None)
            call_command("ensure_superuser", stdout=out)
        self.assertIn("skipping", out.getvalue().lower())
        self.assertEqual(User.objects.count(), 0)

    def test_creates_superuser_from_env(self):
        out = StringIO()
        with mock.patch.dict(os.environ, ENV):
            call_command("ensure_superuser", stdout=out)
        user = User.objects.get()
        self.assertEqual(user.phone, "+256771234567")
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.check_password("strongpass123"))
        self.assertEqual(user.first_name, "Ada")
        self.assertEqual(user.last_name, "Lovelace")

    def test_idempotent_when_user_exists(self):
        with mock.patch.dict(os.environ, ENV):
            call_command("ensure_superuser", stdout=StringIO())
            out = StringIO()
            call_command("ensure_superuser", stdout=out)
        self.assertEqual(User.objects.count(), 1)
        self.assertIn("already exists", out.getvalue().lower())

    def test_invalid_phone_skips_without_creating(self):
        out = StringIO()
        bad = {**ENV, "DJANGO_SUPERUSER_PHONE": "12345"}
        with mock.patch.dict(os.environ, bad):
            call_command("ensure_superuser", stdout=out, stderr=out)
        self.assertEqual(User.objects.count(), 0)
        self.assertIn("invalid", out.getvalue().lower())
```

- [ ] **Step 3: Run the test to verify it fails**

Run:
```bash
cd /Users/mac/projects/jango_mobileapp/backend
source ../.venv/bin/activate
python manage.py test accounts.tests.test_ensure_superuser -v 2
```
Expected: FAIL — `CommandError: Unknown command: 'ensure_superuser'`.

- [ ] **Step 4: Implement the command**

Create `backend/accounts/management/commands/ensure_superuser.py`:

```python
"""Idempotently create a superuser from environment variables.

For hosts without interactive shell access (e.g. Render's free tier). Safe to
run on every deploy: it no-ops when the env vars are unset, when the phone is
invalid, or when the user already exists.

Env vars:
    DJANGO_SUPERUSER_PHONE       (required to do anything)
    DJANGO_SUPERUSER_PASSWORD    (required to do anything)
    DJANGO_SUPERUSER_FIRST_NAME  (optional, default "Admin")
    DJANGO_SUPERUSER_LAST_NAME   (optional, default "User")
"""

import os

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from accounts.validators import normalize_uganda_phone


class Command(BaseCommand):
    help = "Create a superuser from DJANGO_SUPERUSER_* env vars if it does not exist."

    def handle(self, *args, **options):
        phone = os.environ.get("DJANGO_SUPERUSER_PHONE")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        if not phone or not password:
            self.stdout.write(
                "ensure_superuser: DJANGO_SUPERUSER_PHONE/PASSWORD not set; skipping."
            )
            return

        try:
            phone = normalize_uganda_phone(phone)
        except ValidationError:
            self.stderr.write(
                "ensure_superuser: invalid DJANGO_SUPERUSER_PHONE; skipping."
            )
            return

        user_model = get_user_model()
        if user_model.objects.filter(phone=phone).exists():
            self.stdout.write(
                f"ensure_superuser: {phone} already exists; nothing to do."
            )
            return

        user_model.objects.create_superuser(
            phone=phone,
            password=password,
            first_name=os.environ.get("DJANGO_SUPERUSER_FIRST_NAME", "Admin"),
            last_name=os.environ.get("DJANGO_SUPERUSER_LAST_NAME", "User"),
        )
        self.stdout.write(
            self.style.SUCCESS(f"ensure_superuser: created superuser {phone}.")
        )
```

- [ ] **Step 5: Run the test to verify it passes**

Run:
```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py test accounts.tests.test_ensure_superuser -v 2
```
Expected: `Ran 4 tests` ... `OK`.

- [ ] **Step 6: Run the full accounts suite (no regressions)**

Run: `python manage.py test accounts`
Expected: `OK`.

- [ ] **Step 7: Commit**

```bash
cd /Users/mac/projects/jango_mobileapp
git add backend/accounts/management backend/accounts/tests/test_ensure_superuser.py
git commit -m "feat(accounts): add idempotent ensure_superuser management command"
```

---

## Task 5: `render.yaml` blueprint

**Files:**
- Create: `render.yaml` (repo root)

- [ ] **Step 1: Create the blueprint**

Create `render.yaml`:

```yaml
services:
  - type: web
    name: jango-backend
    runtime: python
    plan: free
    branch: deploy/render
    buildCommand: >-
      pip install -r requirements.txt &&
      cd backend &&
      python manage.py collectstatic --no-input &&
      python manage.py migrate &&
      python manage.py ensure_superuser
    startCommand: cd backend && gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT
    healthCheckPath: /api/schema/
    envVars:
      - key: PYTHON_VERSION
        value: "3.12.8"
      - key: SECRET_KEY
        generateValue: true
      - key: DEBUG
        value: "False"
      - key: WEB_CONCURRENCY
        value: "2"
      - key: ALLOWED_HOSTS
        sync: false
      - key: CORS_ALLOWED_ORIGINS
        sync: false
      - key: CSRF_TRUSTED_ORIGINS
        sync: false
      - key: DATABASE_URL
        sync: false
      - key: USE_S3
        value: "False"
      - key: DJANGO_SUPERUSER_PHONE
        sync: false
      - key: DJANGO_SUPERUSER_PASSWORD
        sync: false
      - key: DJANGO_SUPERUSER_FIRST_NAME
        sync: false
      - key: DJANGO_SUPERUSER_LAST_NAME
        sync: false
```

Notes for the implementer:
- `branch: deploy/render` lets the blueprint be applied before the merge to `main`. Change to `main` once merged (Task 8 / follow-up).
- No `databases:` block — nothing is auto-provisioned.
- `sync: false` means "prompt me in the dashboard, don't store in the repo".

- [ ] **Step 2: Validate YAML syntax**

Run:
```bash
cd /Users/mac/projects/jango_mobileapp
python -c "import yaml, sys; d = yaml.safe_load(open('render.yaml')); svc = d['services'][0]; assert svc['type'] == 'web' and svc['plan'] == 'free' and svc['startCommand'].startswith('cd backend'); print('render.yaml OK:', svc['name'])"
```
Expected: `render.yaml OK: jango-backend`

- [ ] **Step 3: Verify the build command works locally (simulate Render)**

Run:
```bash
cd /Users/mac/projects/jango_mobileapp
source .venv/bin/activate
rm -f backend/db.sqlite3
cd backend
DEBUG=False SECRET_KEY=dummy python manage.py collectstatic --no-input
DEBUG=False SECRET_KEY=dummy python manage.py migrate
DEBUG=False SECRET_KEY=dummy python manage.py ensure_superuser
```
Expected: `collectstatic` reports files copied and post-processed (WhiteNoise manifest); `migrate` applies all migrations to the fresh SQLite file with no error; `ensure_superuser` prints `... not set; skipping.` (no superuser env vars locally).

- [ ] **Step 4: Verify gunicorn boots the app**

Run:
```bash
cd /Users/mac/projects/jango_mobileapp/backend
DEBUG=False SECRET_KEY=dummy ALLOWED_HOSTS=127.0.0.1,localhost \
  ../.venv/bin/gunicorn backend.wsgi:application --bind 127.0.0.1:8123 --workers 1 &
GUNICORN_PID=$!
sleep 4
curl -sS -o /dev/null -w "schema: %{http_code}\n" http://127.0.0.1:8123/api/schema/
curl -sS -o /dev/null -w "admin:  %{http_code}\n" http://127.0.0.1:8123/admin/login/
kill $GUNICORN_PID
```
Expected: `schema: 200` and `admin: 200`. If `admin` returns 500, check that `collectstatic` ran (WhiteNoise manifest storage needs `staticfiles/` populated).

- [ ] **Step 5: Clean up the simulation artifacts**

Run:
```bash
cd /Users/mac/projects/jango_mobileapp
rm -f backend/db.sqlite3
rm -rf backend/staticfiles
```
(`db.sqlite3` and `staticfiles/` are already git-ignored; this just keeps the tree tidy.)

- [ ] **Step 6: Commit**

```bash
git add render.yaml
git commit -m "feat: add render.yaml blueprint for free-tier deploy"
```

---

## Task 6: Repository cleanup

**Files:**
- Delete: `backend/.env.production`
- Modify: `.gitignore`
- Modify: `backend/.env.example`

- [ ] **Step 1: Remove the committed production env file**

Run:
```bash
cd /Users/mac/projects/jango_mobileapp
git rm backend/.env.production
```
Expected: `rm 'backend/.env.production'`

- [ ] **Step 2: Tighten `.gitignore`**

In `.gitignore`, replace the line:
```
.env
```
with:
```
.env
.env.*
!.env.example
```

- [ ] **Step 3: Rewrite `backend/.env.example`**

Write `backend/.env.example` exactly as:

```
# Core
SECRET_KEY=
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=
CORS_ALLOWED_ORIGINS=

# Database. Leave unset for a local SQLite file (backend/db.sqlite3).
# Postgres example: postgresql://user:pass@host:5432/dbname
DATABASE_URL=

# JWT lifetimes
JWT_ACCESS_MINUTES=60
JWT_REFRESH_DAYS=7

# Media storage. Set USE_S3=True plus the AWS_* vars to store uploads in an
# S3-compatible bucket (AWS S3 / Cloudflare R2 / Backblaze B2).
USE_S3=False
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
# AWS_STORAGE_BUCKET_NAME=
# AWS_S3_ENDPOINT_URL=
# AWS_S3_REGION_NAME=
# AWS_S3_CUSTOM_DOMAIN=

# Superuser bootstrap (used by `manage.py ensure_superuser` on deploy hosts
# without shell access). PHONE must be a valid Uganda number.
# DJANGO_SUPERUSER_PHONE=
# DJANGO_SUPERUSER_PASSWORD=
# DJANGO_SUPERUSER_FIRST_NAME=Admin
# DJANGO_SUPERUSER_LAST_NAME=User
```

- [ ] **Step 4: Confirm nothing still reads the removed `DB_*` vars**

Run:
```bash
cd /Users/mac/projects/jango_mobileapp
grep -rn --include='*.py' -E 'DB_NAME|DB_USER|DB_PASSWORD|DB_HOST|DB_PORT' backend | grep -v '/.venv/'
```
Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add .gitignore backend/.env.example backend/.env.production
git commit -m "chore: drop committed .env.production, document new env vars"
```

Note for the operator (out of scope to fix here): the DB password previously committed in `backend/.env.production` remains in git history and should be rotated on the Namecheap side.

---

## Task 7: Operator runbook `DEPLOY-RENDER.md`

**Files:**
- Create: `DEPLOY-RENDER.md` (repo root)

- [ ] **Step 1: Write the runbook**

Create `DEPLOY-RENDER.md`:

```markdown
# Deploying the Jango backend to Render

Free-tier deployment driven by `render.yaml`. See
`docs/superpowers/specs/2026-09-06-render-deploy-design.md` for rationale.

## First deploy

1. Push the branch (`deploy/render`, or merge to `main` and set `branch: main`
   in `render.yaml` first).
2. Render dashboard -> **New** -> **Blueprint** -> connect this repo -> **Apply**.
3. When prompted, fill the `sync: false` env vars:
   - `ALLOWED_HOSTS` - optional; `RENDER_EXTERNAL_HOSTNAME` already covers the
     `*.onrender.com` host. Add custom domains here later, comma-separated.
   - `CORS_ALLOWED_ORIGINS` - the mobile app / web frontend origins.
   - `CSRF_TRUSTED_ORIGINS` - only needed for extra admin origins.
   - `DATABASE_URL` - leave blank for now (ephemeral SQLite). See "Persist the
     database" below.
   - `DJANGO_SUPERUSER_PHONE` / `DJANGO_SUPERUSER_PASSWORD` /
     `DJANGO_SUPERUSER_FIRST_NAME` / `DJANGO_SUPERUSER_LAST_NAME` - the admin
     account created on each deploy. Phone must be a valid Uganda number
     (e.g. `+256771234567`).
4. Wait for build + deploy. Health check: `GET /api/schema/` -> 200.
5. Verify: `/api/docs/`, a public catalogue endpoint, and `/admin/` login with
   the superuser above.

## What "free" costs you

- The service sleeps after 15 min idle; the next request takes ~1 min.
- **SQLite data resets on every deploy/restart.** Fine for testing the
  pipeline and frontend integration; not for real data. Migrations re-run
  each deploy so the schema is always current.
- Uploaded images are also wiped on redeploy unless S3 media is enabled.

## Persist the database (no code change)

Set `DATABASE_URL` on the service and redeploy. `psycopg` is already bundled.

- **Neon** (recommended) - free Postgres that does not expire; copy the pooled
  connection string.
- **Supabase** - free Postgres, 500 MB, pauses when idle.
- **Render PostgreSQL** - deleted 30 days after creation unless upgraded ($7/mo).

Format: `postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require`

## Persist uploaded media (Cloudflare R2, free tier)

1. Cloudflare -> R2 -> create bucket `jango-media`.
2. Create an R2 API token (Object Read & Write); note the Access Key ID + Secret.
3. On the Render service set: `USE_S3=True`, `AWS_ACCESS_KEY_ID`,
   `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME=jango-media`,
   `AWS_S3_ENDPOINT_URL=https://<accountid>.r2.cloudflarestorage.com`,
   `AWS_S3_CUSTOM_DOMAIN=<public bucket or CDN host>`.
4. Redeploy. Same vars work for AWS S3 (drop the endpoint, set
   `AWS_S3_REGION_NAME`) and Backblaze B2.

## Custom domain

Render service -> Settings -> Custom Domains -> add `api.jangumobile.com`,
create the shown CNAME at the DNS provider, then add the host to
`ALLOWED_HOSTS` and (if admin is used from it) `CSRF_TRUSTED_ORIGINS`.

## Troubleshooting

- **`DisallowedHost`** - add the host to `ALLOWED_HOSTS`.
- **Admin/DRF pages unstyled or 500 on a static asset** - the build's
  `collectstatic` step failed; check build logs.
- **CSRF failures on admin login** - add `https://<host>` to
  `CSRF_TRUSTED_ORIGINS`.
- **Health check failing** - confirm `/api/schema/` returns 200 locally under
  gunicorn; check `DEBUG=False` didn't leave `ALLOWED_HOSTS` empty (it's fine,
  `RENDER_EXTERNAL_HOSTNAME` is appended automatically).

## Rollback

Render keeps prior deploys - use **Rollback** in the dashboard. The
Namecheap/cPanel + MySQL deploy is untouched and remains the fallback.
```

- [ ] **Step 2: Commit**

```bash
cd /Users/mac/projects/jango_mobileapp
git add DEPLOY-RENDER.md
git commit -m "docs: add Render deployment runbook"
```

---

## Task 8: Final full verification

**Files:** none (verification gate)

- [ ] **Step 1: Fresh dependency install from scratch**

Run:
```bash
cd /Users/mac/projects/jango_mobileapp
python3.12 -m venv /tmp/jango-render-verify 2>/dev/null || python3 -m venv /tmp/jango-render-verify
/tmp/jango-render-verify/bin/pip install --quiet --upgrade pip
/tmp/jango-render-verify/bin/pip install -r requirements.txt
```
Expected: completes with no `ERROR`. (If `python3.12` is unavailable locally, the default `python3` is an acceptable proxy; Render itself uses 3.12.8 via `PYTHON_VERSION`.)

- [ ] **Step 2: Build + boot simulation in the clean venv**

Run:
```bash
cd /Users/mac/projects/jango_mobileapp/backend
rm -f db.sqlite3 && rm -rf staticfiles
export DJANGO_SETTINGS_MODULE=backend.settings DEBUG=False SECRET_KEY=verify-only
/tmp/jango-render-verify/bin/python manage.py collectstatic --no-input
/tmp/jango-render-verify/bin/python manage.py migrate
/tmp/jango-render-verify/bin/python manage.py check --deploy
/tmp/jango-render-verify/bin/gunicorn backend.wsgi:application --bind 127.0.0.1:8124 --workers 1 &
GPID=$!; sleep 4
curl -sS -o /dev/null -w "schema %{http_code}\n" http://127.0.0.1:8124/api/schema/
curl -sS -o /dev/null -w "products %{http_code}\n" http://127.0.0.1:8124/api/products/
kill $GPID
```
Expected: `collectstatic`/`migrate` succeed; `check --deploy` shows only `W004`/`W008` warnings; `schema 200`; `products 200`.

- [ ] **Step 2b: Superuser bootstrap end to end**

Run:
```bash
cd /Users/mac/projects/jango_mobileapp/backend
export DJANGO_SUPERUSER_PHONE=+256771234567 DJANGO_SUPERUSER_PASSWORD=verifypass123
export DJANGO_SUPERUSER_FIRST_NAME=Ver DJANGO_SUPERUSER_LAST_NAME=Ify
/tmp/jango-render-verify/bin/python manage.py ensure_superuser
/tmp/jango-render-verify/bin/python manage.py ensure_superuser
unset DJANGO_SUPERUSER_PHONE DJANGO_SUPERUSER_PASSWORD DJANGO_SUPERUSER_FIRST_NAME DJANGO_SUPERUSER_LAST_NAME
```
Expected: first run prints `created superuser +256771234567`, second prints `already exists`.

- [ ] **Step 3: Full test suite (local venv)**

Run:
```bash
cd /Users/mac/projects/jango_mobileapp/backend
../.venv/bin/python manage.py test
```
Expected: `OK`, zero failures/errors.

- [ ] **Step 4: Tidy up**

Run:
```bash
rm -rf /tmp/jango-render-verify
cd /Users/mac/projects/jango_mobileapp/backend && rm -f db.sqlite3 && rm -rf staticfiles
cd /Users/mac/projects/jango_mobileapp && git status
```
Expected: `working tree clean` (all changes already committed across Tasks 2-7).

- [ ] **Step 5: Summary for the user**

Report: branch `deploy/render` with commits for deps, settings, `ensure_superuser`, `render.yaml`, cleanup, and the runbook; all local verification green. Next action is theirs: push the branch and apply the blueprint in the Render dashboard per `DEPLOY-RENDER.md` (they must create the Render account / connect the repo / fill secret env vars — none of that can be done from here).

---

## Self-Review

**Spec coverage:**
- Goals: reproducible blueprint (Task 5), free tier no add-ons (Task 5, `plan: free`, no `databases:`), gunicorn + WhiteNoise (Tasks 2-3), additive/back-compat settings + tests pass (Task 3 steps 7-8), env-var-only upgrades (Task 3 step 5 S3 block, step 4 DATABASE_URL) — covered.
- §6.1 requirements — Task 2.
- §6.2 settings (imports, hosts/CSRF, middleware, DATABASE_URL, STORAGES, USE_S3, security) — Task 3 steps 1-6.
- §6.3 render.yaml — Task 5 (superuser step appended per §6.3 note + §9.2).
- §6.4 Python version — Task 5 (`PYTHON_VERSION: "3.12.8"` env var; `.python-version` file was optional in spec, omitted for a single source of truth — noted).
- §6.5 repo cleanup (.env.production, .gitignore, credential-rotation flag) — Task 6.
- §7 R2 media steps — Task 7 runbook + Task 3 S3 block.
- §8 DB upgrade path — Task 7 runbook.
- §9 operational procedures — Task 7 runbook; §9.2 superuser — Task 4 + wired in Task 5.
- §10 verification — Tasks 3 (steps 7-9), 5 (steps 3-4), 8.
- §11 rollback — Task 7 runbook.

**Placeholder scan:** No TBD/TODO. Every code step has complete content. Commands have expected output.

**Type/name consistency:** `ensure_superuser` command name matches across Task 4 (implementation + tests) and Task 5 (`render.yaml` buildCommand) and Task 7/8 (`manage.py ensure_superuser`). Env var names (`DJANGO_SUPERUSER_PHONE/PASSWORD/FIRST_NAME/LAST_NAME`) identical in command, tests, `render.yaml`, `.env.example`, runbook. `STORAGES` dict keys (`default`, `staticfiles`) match Django 5.2's expected schema. `USE_S3` name consistent across settings, `render.yaml`, `.env.example`, runbook.
