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

- The service sleeps after 15 min idle; the next request takes ~1 min. An
  external uptime pinger (cron-job.org) hits
  `https://<service>.onrender.com/api/schema/` every ~10 min to hold it awake.
  (GitHub Actions is not used for this — Actions is billing-blocked on this repo.)
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
