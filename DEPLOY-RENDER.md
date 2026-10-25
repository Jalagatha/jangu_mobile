# Deploying the Jango backend to Render

Free-tier deployment driven by `render.yaml`. See
`docs/superpowers/specs/2026-09-06-render-deploy-design.md` for rationale.

## First deploy

1. Push the branch (`deploy/render`, or merge to `main` and set `branch: main`
   in `render.yaml` first).
2. Render dashboard -> **New** -> **Blueprint** -> connect this repo -> **Apply**.
3. When prompted, fill the `sync: false` env vars:
   - `CSRF_TRUSTED_ORIGINS` - only needed for extra admin origins.
   (Hosts and CORS are open to all in `settings.py` for the Flutter app, so
   there is no `ALLOWED_HOSTS` / `CORS_ALLOWED_ORIGINS` to fill.)
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

## Catalogue data (products, prices, stock, images)

The shop's products live in git, in `backend/catalogue/fixtures/`:
`catalogue.json` (categories, products, variants with price + stock, image
rows) and `media/products/*.jpg`. Every deploy runs `load_catalogue`, which
adds any product whose slug is not in the database yet and copies its images
into media storage. Products already in the database are never touched.

To change the catalogue:

1. Locally: `python manage.py load_catalogue`, then edit products in `/admin/`
   (add, re-price, restock, swap photos).
2. `python manage.py dump_catalogue` rewrites `catalogue.json` and copies
   every image the catalogue uses into `fixtures/media/`.
3. Commit and push. Or skip 1-2 and edit `catalogue.json` by hand. Rows
   reference each other by slug/SKU, so you can copy a product block and
   change its values.

While the database is ephemeral SQLite, each deploy rebuilds the shop from
these files, and edits made in the live admin are lost. Once `DATABASE_URL`
is set, the live admin is the source of truth: deploys only add new products
from the fixture and never overwrite live prices or stock.

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
create the shown CNAME at the DNS provider, then (if admin is used from it)
add `https://<host>` to `CSRF_TRUSTED_ORIGINS`.

## Troubleshooting

- **Admin/DRF pages unstyled or 500 on a static asset** - the build's
  `collectstatic` step failed; check build logs.
- **CSRF failures on admin login** - add `https://<host>` to
  `CSRF_TRUSTED_ORIGINS`.
- **Health check failing** - confirm `/api/schema/` returns 200 locally under
  gunicorn and check the deploy logs.

## Rollback

Render keeps prior deploys - use **Rollback** in the dashboard. The
Namecheap/cPanel + MySQL deploy is untouched and remains the fallback.
