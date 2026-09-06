# Render deployment — design

- **Date:** 2026-09-06
- **Status:** Approved (design), pending implementation plan
- **Author:** Mugisha Ivan Jalagatha

## 1. Context

`jango_mobileapp` is a Django 5.2 REST API backend (`backend/` subdirectory) with apps
`core`, `accounts` (phone-based JWT auth, custom `User` model), and `catalogue`
(products, variants, image uploads, staff CRUD). It is currently deployed on Namecheap
cPanel shared hosting via Phusion Passenger (`backend/passenger_wsgi.py`) against a
**MySQL** database, for the domain `jangumobile.com`.

We want to run it on **Render** as the new production home, initially on the
`*.onrender.com` URL (no custom domain yet), at **zero cost**, defined by a
`render.yaml` blueprint committed to the repo.

Application code is database-agnostic — only `backend/backend/settings.py` names MySQL
(`ENGINE` + `charset` option). There is no raw SQL in app code.

## 2. Goals

- One-command, reproducible deploy from a `render.yaml` blueprint.
- Runs on Render's **free** web service tier with **no paid add-ons** and **no
  externally-provisioned database** required for the first deploy.
- `gunicorn` app server; static assets (admin, DRF browsable API) served by the app.
- Settings changes are **additive and backwards-compatible** — local development against
  the existing `backend/.env` + MySQL keeps working unchanged, and the test suite still
  passes.
- Upgrading to a persistent database or object storage later is a **configuration
  change only** (set environment variables + redeploy), never a code change.

## 3. Non-goals

- Migrating existing data out of the Namecheap MySQL database. Render starts with a
  fresh, empty database.
- Zero-downtime deploys or horizontal scaling (not possible on the free tier).
- Keeping MySQL. Render offers no managed MySQL; the project moves to PostgreSQL
  (or SQLite) going forward.
- Custom domain / DNS setup, CI beyond Render's built-in auto-deploy, background
  workers, cron jobs, Redis/caching, and the not-yet-implemented cart/orders app.

## 4. Constraints — Render free tier (verified 2026-09-06)

| Concern | Reality |
| --- | --- |
| Free PostgreSQL | Expires **30 days after creation** (14-day grace, then the database and all data are deleted). 1 GB storage, no backups, one per workspace. |
| Persistent disk | **Not available** on free web services. Requires a paid instance ($7/mo) + $0.25/GB. |
| Free web service | No time limit, but **spins down after 15 min idle** (~1 min cold start). 750 instance-hours/month, 512 MB RAM. |
| Container filesystem | Ephemeral — wiped on every deploy and restart. |

**Consequence:** "free + zero-setup + persistent" is not achievable on Render. This
design ships **free and working immediately** with ephemeral SQLite, and pre-wires the
two upgrade paths (Postgres via `DATABASE_URL`, media via S3-compatible object storage)
so they activate with environment variables alone.

## 5. Architecture overview

```
GitHub repo (branch: main)
        │  push
        ▼
Render Blueprint (render.yaml, repo root)
        │
        ▼
Web service "jango-backend" (free plan, Python runtime)
  build:  pip install -r requirements.txt
          cd backend && collectstatic --no-input && migrate
  start:  cd backend && gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT
  ┌─────────────────────────────────────────────┐
  │ gunicorn ── Django (backend.settings)       │
  │   static  ── WhiteNoise  ── ./staticfiles/  │
  │   db      ── dj-database-url(DATABASE_URL)  │
  │             └─ default: sqlite ./db.sqlite3 │  (ephemeral)
  │   media   ── FileSystemStorage ./media/     │  (ephemeral)
  │             └─ if USE_S3: S3/R2/B2 bucket   │  (persistent, opt-in)
  └─────────────────────────────────────────────┘
```

The Django project lives in `backend/`, but `requirements.txt` and `render.yaml` sit at
the repo root. The blueprint therefore installs from the root, then `cd backend` for all
`manage.py` / `gunicorn` invocations. No Render "root directory" override is used, and
no files are moved.

## 6. Detailed changes

### 6.1 `requirements.txt` (repo root)

**Add:**

- `gunicorn` — WSGI app server.
- `whitenoise[brotli]` — static file serving from the app process.
- `dj-database-url` — parse `DATABASE_URL` into Django's `DATABASES`.
- `psycopg[binary]` — PostgreSQL driver, so a Postgres `DATABASE_URL` works with no
  further changes when the user chooses to add one.
- `django-storages` + `boto3` — S3-compatible media backend, dormant until `USE_S3=true`.

**Remove:**

- `mysqlclient` — needs system build dependencies not present in Render's Python
  environment (build would fail), and is unused after the move off MySQL.

All new packages pinned to their latest versions compatible with Django 5.2 and
Python 3.12, consistent with the file's existing fully-pinned style.

> **Local-dev note:** developers currently on MySQL must either re-install
> `mysqlclient` locally *or* switch their `backend/.env` to a local Postgres/SQLite
> `DATABASE_URL`. Document this in the implementation plan's manual-steps section.

### 6.2 `backend/backend/settings.py`

All changes are additive. Reading `backend/.env` via `django-environ` stays (silent
no-op on Render, which injects real environment variables).

**Imports:** add `import os` and `import dj_database_url`.

**Hosts & CSRF** — replace the single `ALLOWED_HOSTS` line with:

```python
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")
```

Render injects `RENDER_EXTERNAL_HOSTNAME`, so the service is reachable and admin login
works even before `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` env vars are set.

**Middleware** — insert directly after `SecurityMiddleware`:

```python
"whitenoise.middleware.WhiteNoiseMiddleware",
```

**Database** — replace the hard-coded MySQL `DATABASES` block with:

```python
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}
```

`dj_database_url.config()` reads `DATABASE_URL` from the environment; absent it, falls
back to a local SQLite file (`backend/db.sqlite3`, already git-ignored). It parses
`postgres://` and `sqlite://` URLs directly with the drivers we ship; a `mysql://` URL
would additionally need a MySQL driver re-added to `requirements.txt`. One line now
covers SQLite (default) and Postgres (the intended upgrade).

**Static files storage** — after the existing `STATIC_ROOT` line:

```python
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
```

Manifest storage only in production, so local `DEBUG=True` dev without a `collectstatic`
run does not raise "missing manifest entry".

**Optional S3/R2/B2 media** — after `MEDIA_ROOT`:

```python
USE_S3 = env.bool("USE_S3", default=False)
if USE_S3:
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default=None)   # R2/B2 endpoint
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default=None)
    AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN", default=None) # public/CDN host
    AWS_QUERYSTRING_AUTH = env.bool("AWS_QUERYSTRING_AUTH", default=False)
    AWS_DEFAULT_ACL = None
    STORAGES["default"]["BACKEND"] = "storages.backends.s3.S3Storage"
```

**Production security** — new block at the end of the file:

```python
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
```

Render terminates TLS at its proxy and forwards `X-Forwarded-Proto`, so the proxy
header is required for `SECURE_SSL_REDIRECT` to behave. HSTS defaults to `0` (off) to
avoid pinning a domain to HTTPS during early testing; bump to `31536000` via env var
once stable.

### 6.3 `render.yaml` (repo root, new file)

```yaml
services:
  - type: web
    name: jango-backend
    runtime: python
    plan: free
    branch: main
    buildCommand: >-
      pip install -r requirements.txt &&
      cd backend &&
      python manage.py collectstatic --no-input &&
      python manage.py migrate
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
        sync: false          # optional; RENDER_EXTERNAL_HOSTNAME covers the default host
      - key: CORS_ALLOWED_ORIGINS
        sync: false
      - key: CSRF_TRUSTED_ORIGINS
        sync: false
      - key: DATABASE_URL
        sync: false          # unset -> ephemeral SQLite; set -> Postgres/other
      - key: USE_S3
        value: "False"
```

- No `databases:` block — nothing is auto-created, matching the "don't provision a
  database" requirement.
- `healthCheckPath: /api/schema/` — drf-spectacular serves the schema with `AllowAny`,
  so it returns 200 without auth.
- `migrate` runs in `buildCommand` (single free instance; `preDeployCommand` is a paid
  feature).
- `gunicorn` reads `WEB_CONCURRENCY` for its worker count automatically.
- The optional superuser-bootstrap step (§9.2) is appended to `buildCommand` by the
  implementation plan; it is omitted here to keep the base blueprint readable.

### 6.4 Python version

Local dev runs Python 3.14, which predates stable wheel coverage for some pinned
dependencies. Render is pinned to **3.12.8** via `PYTHON_VERSION` (well-supported by
Django 5.2, `psycopg[binary]`, `pillow`). Optionally also commit a repo-root
`.python-version` with `3.12.8` for parity.

### 6.5 Repository cleanup

- `git rm backend/.env.production` and add `.env.production` / `.env.*` (keeping
  `!.env.example`) to `.gitignore`. That file currently commits a real DB password;
  Render configuration lives in the dashboard / blueprint instead.
- Flag for the user (out of scope to fix here): the credential exposed in
  `backend/.env.production` git history should be rotated on the Namecheap side.

## 7. Media storage — deferred activation (Cloudflare R2, free)

Cloudflare R2 free tier: 10 GB storage, no egress fees. To turn it on later, with **no
code change**:

1. Create a Cloudflare account → R2 → create a bucket (e.g. `jango-media`).
2. Create an R2 API token (Object Read & Write) → note Access Key ID + Secret.
3. In the Render service, set env vars:
   - `USE_S3=True`
   - `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
   - `AWS_STORAGE_BUCKET_NAME=jango-media`
   - `AWS_S3_ENDPOINT_URL=https://<accountid>.r2.cloudflarestorage.com`
   - `AWS_S3_CUSTOM_DOMAIN=<public bucket or CDN host>` (for public image URLs)
4. Redeploy. New uploads land in R2; existing ephemeral files (if any) are re-uploaded
   through the staff API.

The same variables work for AWS S3 (omit `AWS_S3_ENDPOINT_URL`, set
`AWS_S3_REGION_NAME`) and Backblaze B2 (B2's S3 endpoint).

## 8. Database — upgrade path

Ephemeral SQLite is fine for pipeline validation and frontend integration, but **all
data resets on every deploy/restart**. When real data must persist, set `DATABASE_URL`
on the Render service and redeploy — no code change (`psycopg` is already installed):

- **Neon** (recommended) — free Postgres, does **not** expire like Render's, generous
  free tier, connection-pooled URL.
- **Supabase** — free Postgres, 500 MB, pauses after inactivity.
- **Render PostgreSQL** — closest integration, but the free instance is deleted 30 days
  after creation; only sensible if paying the $7/mo upgrade before expiry.

Paste the provider's connection string as `DATABASE_URL`
(`postgresql://user:pass@host/dbname?sslmode=require`), redeploy; `migrate` in the build
creates the schema.

## 9. Operational procedures

### 9.1 First deploy

1. Merge the implementation branch to `main`.
2. In Render: **New → Blueprint**, connect the repo, apply `render.yaml`.
3. Wait for build + deploy; confirm the health check passes.
4. Set any needed env vars (`CORS_ALLOWED_ORIGINS` for the mobile app / frontend, etc.),
   then trigger a redeploy if changed.

### 9.2 Creating the admin user (no shell on free tier)

The custom user model uses `USERNAME_FIELD = "phone"` with
`REQUIRED_FIELDS = ["first_name", "last_name"]`, and `phone` must pass the Uganda phone
validator. Add a guarded step to `buildCommand` (or a tiny idempotent management
command) driven by env vars:

```
python manage.py createsuperuser --no-input || true
```

with `DJANGO_SUPERUSER_PHONE`, `DJANGO_SUPERUSER_FIRST_NAME`,
`DJANGO_SUPERUSER_LAST_NAME`, `DJANGO_SUPERUSER_PASSWORD` set on the service
(`|| true` so redeploys don't fail once the user exists). The implementation plan
decides between this and a dedicated `ensure_superuser` command; the command is cleaner
because it can no-op silently and validate the phone.

### 9.3 Migrations

Run automatically in `buildCommand` on every deploy.

### 9.4 Cold starts

Free services sleep after 15 min idle; the first request then takes ~1 min. Acceptable
for now. An external uptime pinger or the $7/mo plan removes it later.

### 9.5 Custom domain (future, out of scope)

Render → service → Settings → Custom Domains; add `api.jangumobile.com`, create the
CNAME at the DNS provider, add the host to `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS`.

## 10. Verification

**Local (before merge):**

- `cd backend && python manage.py check`
- `cd backend && python manage.py test` — full suite passes on the new SQLite default.
- Clean virtualenv: `pip install -r requirements.txt` succeeds without `mysqlclient`.
- `cd backend && python manage.py collectstatic --no-input` succeeds.
- `cd backend && DEBUG=False SECRET_KEY=x gunicorn backend.wsgi:application` boots.

**Post-deploy (on Render):**

- `GET /api/schema/` and `/api/docs/` → 200.
- A public catalogue endpoint (e.g. `GET /api/products/`) → 200 JSON.
- `/admin/` → login page renders with CSS (WhiteNoise working); superuser can log in.
- `POST /api/auth/` register/login flow returns JWTs.
- `python manage.py check --deploy` reports no critical warnings with `DEBUG=False`.

## 11. Rollback

- Render keeps prior deploys — use **Rollback** in the dashboard to revert a bad deploy.
- The Namecheap/cPanel + MySQL deployment is left untouched and remains the fallback
  until Render is confirmed healthy.
- If the `settings.py` changes disrupt local dev, revert the single implementation
  commit; changes are self-contained.

## 12. Open questions

None blocking. Deferred decisions (object storage provider, persistent DB provider,
custom domain) are all configuration-only and documented above.
