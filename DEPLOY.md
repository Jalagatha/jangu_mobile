# Deploying Jangu Mobile

The backend and website run on a Namecheap VPS at `jangumobile.site`. The server also
hosts other sites, so everything Jangu needs has its own name and nothing else on the
server is changed.

| Piece | Where |
| --- | --- |
| Code | `/srv/jangu/app`, updated with `git pull` using a read-only deploy key |
| Python environment | `/srv/jangu/venv` |
| Settings and secrets | `/srv/jangu/app/backend/.env`, generated on the server and never in git |
| App process | `jangu` systemd service: gunicorn on `/run/jangu/gunicorn.sock` |
| Web server | `/etc/nginx/sites-available/jangu`, which also serves `/media/` |
| Database | Postgres database and role, both named `jangu` |

## Deploy an update

Push to `main`, then:

    ssh root@66.29.151.131 /srv/jangu/app/deploy/update.sh

This pulls the code, installs requirements, collects static files, runs migrations, adds
any new catalogue products, restarts the app, and fails if the app does not respond.

## First deploy

Run from the repo root on a machine whose SSH key the server accepts.

1. At Namecheap, under Advanced DNS, add `A` records for `@` and `www` pointing to
   `66.29.151.131`.
2. Set up the server:

       ssh root@66.29.151.131 'bash -s' < deploy/provision.sh

   The first run stops and prints a public key. Save it to a file, add it to GitHub as a
   read-only deploy key, and run the command above again:

       gh repo deploy-key add <file> --repo Jalagatha/jangu_mobile --title jangu-vps

3. Load the data dump. The script refuses to run if the database already has products:

       scp backups/local-data-2026-11-02.json backups/local-media-2026-11-02.tar.gz root@66.29.151.131:/tmp/
       ssh root@66.29.151.131 /srv/jangu/app/deploy/restore.sh /tmp/local-data-2026-11-02.json /tmp/local-media-2026-11-02.tar.gz

4. Start the app:

       ssh root@66.29.151.131 /srv/jangu/app/deploy/update.sh

5. Once the DNS records resolve, turn on HTTPS. Certbot renews the certificate
   automatically after this:

       ssh root@66.29.151.131 certbot --nginx -d jangumobile.site -d www.jangumobile.site --redirect

6. Create the admin account. You choose the password at the prompt, so it stays out of
   files and chat:

       ssh -t root@66.29.151.131 'cd /srv/jangu/app/backend && sudo -u jangu -H /srv/jangu/venv/bin/python manage.py createsuperuser'

## Check that it works

- `https://jangumobile.site/` shows the shop, with product images.
- `https://jangumobile.site/api/products/` returns JSON with `https://` image URLs.
- `https://jangumobile.site/admin/` is styled and accepts the admin login.

The Cypress journey can also run against the live site, but it creates a test shopper:

    cd e2e && CYPRESS_BASE_URL=https://jangumobile.site npm run e2e

## Catalogue data

The shop's products live in git, in `backend/catalogue/fixtures/`: `catalogue.json` plus
`media/products/*.jpg`. Every deploy runs `load_catalogue`, which adds any product whose
slug is not in the database yet. Products already in the database are never touched, so
the live admin is the source of truth for prices and stock.

To ship new products from your machine:

1. Locally, run `python manage.py load_catalogue`, then edit products in `/admin/`.
2. Run `python manage.py dump_catalogue`, which rewrites `catalogue.json` and copies the
   images it uses into `fixtures/media/`.
3. Commit, push and deploy.

## Troubleshooting

    ssh root@66.29.151.131 systemctl status jangu
    ssh root@66.29.151.131 journalctl -u jangu -n 100

- **502 from nginx:** the `jangu` service is down. The commands above show why.
- **Admin login fails:** check that you are on `https://`; session cookies are HTTPS-only.
- **Images on `http://` in the API:** nginx is not sending `X-Forwarded-Proto`.

## Not set up yet

Nothing backs up the production database or `backend/media/`. Set that up before real
orders come in.
