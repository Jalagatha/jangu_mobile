#!/usr/bin/env bash
# Deploy the latest main. Run as root:
#   ssh root@<server> /srv/jangu/app/deploy/update.sh
set -euo pipefail

as_app() { sudo -u jangu -H "$@"; }
manage() { as_app /srv/jangu/venv/bin/python manage.py "$@"; }

# Wrapped in a function so bash has read all of it before git pull can replace this file.
main() {
    cd /srv/jangu/app/backend
    as_app git pull -q --ff-only
    as_app /srv/jangu/venv/bin/pip install -q -r ../requirements.txt
    manage collectstatic --no-input -v 0
    manage migrate --no-input -v 0
    manage load_catalogue
    manage ensure_superuser
    systemctl restart jangu
    curl -fsS -o /dev/null --unix-socket /run/jangu/gunicorn.sock \
        -H 'Host: jangumobile.site' -H 'X-Forwarded-Proto: https' \
        http://localhost/api/schema/
    echo "Deployed $(as_app git log -1 --format='%h %s')"
}

main
