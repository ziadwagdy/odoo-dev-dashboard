#!/bin/sh
set -e

mkdir -p "${DATA_DIR:-/app/data}"

# Trust all directories under ODOO_DEV_BASE (needed when container UID != host UID)
git config --global --add safe.directory '*'

python manage.py migrate --run-syncdb --no-input
python manage.py ensure_groups

exec daphne -b 0.0.0.0 -p 8000 core.asgi:application
