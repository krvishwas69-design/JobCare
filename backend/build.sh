#!/usr/bin/env bash
# Build/release script used by Render (see ../render.yaml). Safe to run repeatedly.
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input
if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
  python manage.py seed_candidates
fi
python manage.py ensure_superuser
